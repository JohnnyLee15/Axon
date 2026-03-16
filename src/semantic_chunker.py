# Suppress logging
import logging
logging.disable(logging.INFO)

from config import *
import torch
import pysbd
from transformers import AutoModel, AutoTokenizer
import re
from chunk_tracker import ChunkTracker, Chunk
from block_tracker import Block
from typing import Callable
from context_buffer_tracker import ContextBufferTracker

class SemanticChunker:
    def __init__(self):
        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        self._device = torch.device("mps")
        self._seg = pysbd.Segmenter(language="en", clean=False)

        self._model = AutoModel.from_pretrained(
            EMBEDDING_MODEL,
            trust_remote_code=True
        ).to(self._device)
        self._model.eval()

        self._tokenizer = AutoTokenizer.from_pretrained(
            EMBEDDING_MODEL,
            trust_remote_code=True
        )


    def _find_ws_cut_idx(
        self,
        tracker: ChunkTracker,
        sentence: str,
        start_idx: int,
        end_idx: int
    ) -> tuple[int, int]:
        ws_match = re.search(r'.*(\s)', sentence[start_idx:end_idx])
        if not ws_match:
            return end_idx, end_idx

        last_ws_idx = start_idx + ws_match.start(1)
        ws_cand = self._add_spacer(tracker.len(), sentence[start_idx:last_ws_idx], spacer=" ")

        if tracker.len() + len(ws_cand) >=  MIN_CHUNK_CHARS:
            return last_ws_idx, last_ws_idx + 1

        return end_idx, end_idx


    def _split_sentence(self, tracker: ChunkTracker, sentence: str) -> None:
        start_idx = 0
        while start_idx < len(sentence):
            spacer_len = 1 if tracker.len() > 0 else 0
            end_idx = start_idx + MAX_CHUNK_CHARS - tracker.len() - spacer_len

            if end_idx >= len(sentence):
                tracker.add_text(self._add_spacer(tracker.len(), sentence[start_idx:], spacer=" "))
                return

            cut_idx, next_start = self._find_ws_cut_idx(tracker, sentence, start_idx, end_idx)
            tracker.add_text(self._add_spacer(tracker.len(), sentence[start_idx:cut_idx], spacer=" "))
            start_idx = next_start
            tracker.flush()


    def _add_or_split(
        self, tracker: ChunkTracker,
        text: str,
        split: Callable
    ) -> None:
        if tracker.len() >= MIN_CHUNK_CHARS:
            tracker.flush()

        if tracker.is_empty() and len(text) <= MAX_CHUNK_CHARS:
            tracker.add_text(text)
            return

        split(tracker, text)


    def _split_block(self, tracker: ChunkTracker, block_text: str) -> None:
        sentences = self._seg.segment(block_text)
        for sentence in sentences:
            cand_text = self._add_spacer(tracker.len(), sentence, spacer=" ")

            if tracker.len() + len(cand_text) <= MAX_CHUNK_CHARS:
                tracker.add_text(cand_text)
            else:
                self._add_or_split(tracker, sentence, self._split_sentence)


    def _add_spacer(self, curr_len: int, text: str, spacer: str) -> str:
        return (spacer if curr_len > 0 else "") + text


    def _process_body(self, tracker: ChunkTracker, block_text: str) -> None:
        cand_text = self._add_spacer(tracker.len(), block_text, spacer="\n\n")
        if tracker.len() + len(cand_text) <= MAX_CHUNK_CHARS:
            tracker.add_text(cand_text)
            return

        self._add_or_split(tracker, block_text, self._split_block)


    def _process_header(self, tracker: ChunkTracker, block_text: str) -> None:
        if tracker.len() >= MIN_CHUNK_CHARS:
            tracker.flush()
        tracker.add_text(self._add_spacer(tracker.len(), block_text, spacer="\n\n"))


    def _build_chunks(self, blocks_reg: dict[int, Block]) -> dict[int, Chunk]:
        tracker = ChunkTracker()
        for bid in sorted(blocks_reg):
            block = blocks_reg[bid]
            block_text = block.markdown

            is_header = (
                block.label == "SECTION_HEADER" and
                len(block_text) <= MAX_HEADER_CHARS
            )

            if is_header:
                self._process_header(tracker, block_text)
            else:
                self._process_body(tracker, block_text)

        tracker.flush()
        return tracker.get_chunks()


    def _build_context_buffers(
        self,
        chunks: dict[int, Chunk]
    ) -> tuple[list[str], list[dict[int, tuple[int, int]]]]:
        tracker = ContextBufferTracker()
        for cid in sorted(chunks):
            chunk_text = chunks[cid].markdown
            cand_text = self._add_spacer(tracker.len(), chunk_text, spacer="\n\n")

            if tracker.len() + len(cand_text) <= MAX_JINA_LARGE_CHUNK_CHARS:
                tracker.add_chunk(cand_text, cid)

            else:
                tracker.flush()
                tracker.add_chunk(chunk_text, cid)

        tracker.flush()
        return tracker.get_context_buffers(), tracker.get_char_map_list()


    def _gen_chunk_embeddings(
        self,
        chunks: dict[int, Chunk],
        context_buffers: list[str],
        char_map_list: list[dict[int, tuple[int, int]]]
    ) -> None:
        for i, context_buffer in enumerate(context_buffers):
            char_map = char_map_list[i]
            tokens = self._tokenizer(
                context_buffer,
                return_tensors="pt",
                return_offsets_mapping=True,
                padding=True,
                truncation=True,
                max_length=8192
            )

            token_ids = tokens["input_ids"].to(self._device)
            padding_mask = tokens["attention_mask"].to(self._device)

            # Grab [0] because HF expects batched inputs, so batched outputs
            offsets = tokens["offsets_mapping"][0].tolist()

            with torch.no_grad():
                output = self._model(input_ids=token_ids, attention_mask=padding_mask)
                enriched_tokens = output.last_hidden_state[0]

            for cid in sorted(char_map):
                token_indices = []
                map_start_idx, map_end_idx = char_map[cid]
                for tok_idx, (tok_start_idx, tok_end_idx) in enumerate(offsets):

                    # skip special tokens like [CLS], [SEP], etc their offsets are (0,0)
                    if tok_start_idx == tok_end_idx == 0:
                        continue

                    if tok_end_idx > map_start_idx and map_end_idx > tok_start_idx:
                        token_indices.append(tok_idx)

                # Edge case should never really happen, we'll skip this block
                if not token_indices:
                    continue

                start_tok_idx = min(token_indices)
                end_tok_idx = max(token_indices) + 1

                token_embeddings = enriched_tokens[start_tok_idx:end_tok_idx, :]
                chunks[cid].embedding = torch.mean(token_embeddings, dim=0)








