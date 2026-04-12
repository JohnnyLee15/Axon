# Suppress logging from other libraries
import logging
import warnings
logging.disable(logging.INFO)
logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from transformers import logging as trans_log
trans_log.set_verbosity_error()
trans_log.disable_progress_bar()

from huggingface_hub.utils import disable_progress_bars, logging as hf_log
hf_log.set_verbosity_error()
disable_progress_bars()

# imports
from config import *
import torch
import pysbd
from transformers import AutoModel, AutoTokenizer
from chunk_tracker import ChunkTracker, Chunk
from document_state import Block
from typing import Callable
from context_buffer_tracker import ContextBufferTracker
from rich.console import Console
from optimum.quanto import quantize, freeze, qint4

class SemanticChunker:
    def __init__(self, console: Console):
        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        # TODO: Implement CPU fallback to int4 or int8 quantization
        self._device = torch.device("mps")
        self._seg = pysbd.Segmenter(language="en", clean=False)

        self._model = AutoModel.from_pretrained(EMBEDDING_MODEL, dtype=torch.float16)
        quantize(self._model, weights=qint4)
        freeze(self._model)
        self._model.to(self._device)
        self._model.eval()

        self._tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
        self._console = console


    def __call__(self, blocks_reg: dict[int, Block]) -> dict[int, Chunk]:
        """Executes the end-to-end chunking and embedding pipeline."""
        chunks = self._build_chunks(blocks_reg)
        context_buffers, char_map_list = self._build_context_buffers(chunks)
        self._gen_chunk_embeddings(chunks, context_buffers, char_map_list)
        return chunks


    def _add_spacer(self, curr_len: int, text: str, spacer: str) -> str:
        return (spacer if curr_len > 0 else "") + text


    def _find_ws_cut_idx(
        self,
        tracker: ChunkTracker,
        sentence: str,
        start_idx: int,
        end_idx: int
    ) -> tuple[int, int]:
        ws_match = WS_RE.search(sentence[start_idx:end_idx])
        if not ws_match:
            return end_idx, end_idx

        last_ws_idx = start_idx + ws_match.start(1)
        ws_cand = self._add_spacer(tracker.len(), sentence[start_idx:last_ws_idx], spacer=" ")

        if tracker.len() + len(ws_cand) >= MIN_CHUNK_CHARS:
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


    def _process_body(self, tracker: ChunkTracker, block_text: str) -> None:
        cand_text = self._add_spacer(tracker.len(), block_text, spacer="\n\n")
        if tracker.len() + len(cand_text) <= MAX_CHUNK_CHARS:
            tracker.add_text(cand_text)
        else:
            self._add_or_split(tracker, block_text, self._split_block)


    def _process_header(self, tracker: ChunkTracker, block_text: str) -> None:
        cand_header = self._add_spacer(tracker.len(), block_text, spacer="\n\n")
        flush_tracker = (
            (tracker.len() >= MIN_CHUNK_CHARS and not tracker.last_was_header()) or
            (tracker.last_was_header() and tracker.len() + len(cand_header) > MAX_HEADER_STACK_CHARS)
        )
        if flush_tracker:
            tracker.flush()
            cand_header = block_text

        tracker.add_text(cand_header, True)


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

            cand_toks_count = len(self._tokenizer(
                tracker.get_curr_buffer() + cand_text,
                return_attention_mask=False,
                return_token_type_ids=False
            )["input_ids"])

            if cand_toks_count <= MAX_JINA_TOKS:
                tracker.add_chunk(cand_text, cid)

            else:
                tracker.flush()
                tracker.add_chunk(chunk_text, cid)

        tracker.flush()
        return tracker.get_context_buffers(), tracker.get_char_map_list()

    def _get_chunk_token_indices(
        self,
        map_start: int,
        map_end: int,
        offsets: list[tuple[int, int]],
        tok_idx: int
    ) -> tuple[list[int], int]:
        token_indices = []
        within_chunk = True
        num_tokens = len(offsets)

        while tok_idx < num_tokens and within_chunk:
            tok_start, tok_end = offsets[tok_idx]
            if tok_start >= map_end:
                within_chunk = False
                continue

            if (tok_start != 0 or tok_end != 0) and tok_end > map_start:
                token_indices.append(tok_idx)
            tok_idx += 1

        # tok_idx - 1 incase the current tok overlaps with characters in the next chunk
        next_tok_idx = max(0, tok_idx - 1)
        return token_indices, next_tok_idx


    def _gen_chunk_embeddings(
        self,
        chunks: dict[int, Chunk],
        context_buffers: list[str],
        char_map_list: list[dict[int, tuple[int, int]]]
    ) -> None:
        cids = []
        embeddings = []
        for i, context_buffer in enumerate(context_buffers):
            char_map = char_map_list[i]
            tokens = self._tokenizer(
                context_buffer,
                return_tensors="pt",
                return_offsets_mapping=True
            )

            token_ids = tokens["input_ids"].to(self._device)
            padding_mask = tokens["attention_mask"].to(self._device)

            # Grab [0] because HF expects batched inputs, so batched outputs
            offsets = tokens["offset_mapping"][0].tolist()

            with torch.no_grad():
                output = self._model(
                    input_ids=token_ids,
                    attention_mask=padding_mask,
                    task="retrieval.passage"
                )
                enriched_tokens = output.last_hidden_state[0]

            tok_idx = 0
            for cid in sorted(char_map):
                map_start, map_end = char_map[cid]
                token_indices, tok_idx = self._get_chunk_token_indices(
                    map_start,
                    map_end,
                    offsets,
                    tok_idx
                )

                start_tok, end_tok = token_indices[0], token_indices[-1] + 1
                embeddings.append(torch.mean(
                    enriched_tokens[start_tok:end_tok, :],
                    dim = 0,
                    dtype=torch.float32
                ))
                cids.append(cid)

        if embeddings:
            stacked = torch.stack(embeddings, dim=0).cpu()
            for idx, cid in enumerate(cids):
                chunks[cid].embedding = stacked[idx].tolist()


    def embed_query(self, query: str) -> list[float]:
        if len(query) > MAX_QUERY_CHARS:
            raise ValueError(f"Query exceeds maximum character limit of {MAX_QUERY_CHARS}")

        tokens = self._tokenizer(query, return_tensors="pt")
        token_ids = tokens["input_ids"].to(self._device)
        padding_mask = tokens["attention_mask"].to(self._device)

        with torch.no_grad():
            output = self._model(
                input_ids=token_ids,
                attention_mask=padding_mask,
                task="retrieval.query"
            )

            enriched_tokens = output.last_hidden_state[0]
            embedding = torch.mean(
                enriched_tokens,
                dim=0,
                dtype=torch.float32
            )

        return embedding.cpu().tolist()