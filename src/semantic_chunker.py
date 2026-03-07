import logging
# Suppress logging
logging.disable(logging.INFO)

import config
import torch
import pysbd
from transformers import AutoModel, AutoTokenizer
import re
from chunk_tracker import ChunkTracker

class SemanticChunker:
    def __init__(self):
        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        self._device = torch.device("mps")
        self._seg = pysbd.Segmenter(language="en", clean=False)

        self._model = AutoModel.from_pretrained(
            config.EMBEDDING_MODEL,
            trust_remote_code=True
        ).to(self._device)
        self._model.eval()

        self._tokenizer = AutoTokenizer.from_pretrained(
            config.EMBEDDING_MODEL,
            trust_remote_code=True
        )


    def _process_oversized_sentence(self, sentence, prefix, sub_blocks):
        start_idx = 0
        while start_idx < len(sentence):
            end_idx = start_idx + config.MAX_JINA_LARGE_CHUNK_CHARS - len(prefix)

            if end_idx >= len(sentence):
                chunk = sentence[start_idx:]
                return f"{prefix}{chunk}"

            ws_match = re.search(r'.*(\s)', sentence[start_idx:end_idx])
            has_space_after_threshold = ws_match and ws_match.start(1) >= config.MIN_SPACE_SPLIT_THRESHOLD_CHARS
            if has_space_after_threshold:
                last_space_idx = start_idx + ws_match.start(1)
                chunk = sentence[start_idx:last_space_idx]
                start_idx = last_space_idx
            else:
                chunk = sentence[start_idx:end_idx]
                start_idx = end_idx

            sub_blocks.append(f"{prefix}{chunk}")

        return ""


    def _split_oversized_block(self, text, prefix):
        sentences = self.seg.segment(text)
        sub_blocks = []
        current_sub = prefix

        for sentence in sentences:
            candidate_len = len(prefix) + len(sentence)
            if len(sentence) > config.MAX_JINA_LARGE_CHUNK_CHARS:
                current_sub = self._process_oversized_sentence(sentence, prefix, sub_blocks)
                continue

            spacer = " " if current_sub != prefix else ""
            candidate_len = len(current_sub) + len(spacer) + len(sentence)
            if candidate_len > config.MAX_JINA_LARGE_CHUNK_CHARS:
                sub_blocks.append(current_sub)
                current_sub = f"{prefix}{sentence}"
            else:
                current_sub += f"{spacer}{sentence}"

        if current_sub and current_sub != prefix:
            sub_blocks.append(current_sub)

        return sub_blocks


    def _process_oversized_block(
        self,
        block_text,
        prefix,
        tracker,
        bid
    ):
        sub_chunks = self._split_oversized_block(block_text, prefix)
        if sub_chunks:
            spacer = "\n\n" if tracker.get_curr_text() else ""
            candidate_len = len(tracker.get_curr_text()) + len(spacer) + len(sub_chunks[0])
            if candidate_len <= config.MAX_JINA_LARGE_CHUNK_CHARS:
                tracker.add_text(f"{spacer}{sub_chunks.pop(0)}", bid)

            tracker.flush()

            for chunk in sub_chunks[:-1]:
                tracker.add_text(chunk, bid)
                tracker.flush()

            if sub_chunks:
                tracker.add_text(sub_chunks[-1], bid)


    def _process_regular_block(
        self,
        block_text,
        prefix,
        current_header,
        tracker,
        bid
    ):
        full_entry = f"{prefix}{block_text}"
        spacer = "\n\n" if tracker.get_curr_text() else ""

        candidate_len = len(tracker.get_curr_text()) + len(spacer) + len(full_entry)
        if candidate_len > config.MAX_JINA_LARGE_CHUNK_CHARS:
            tracker.flush()
            next_block_text = f"{current_header}:\n{block_text}" if current_header else block_text
            tracker.add_text(next_block_text, bid)
            return

        tracker.add_text(f"{spacer}{full_entry}", bid)


    def _build_large_blocks(self, blocks_reg):
        tracker = ChunkTracker()
        current_header = ""
        last_header= ""

        # TODO: Handle table items better
        for bid in sorted(blocks_reg.keys()):
            block = blocks_reg[bid]
            block_text = block.markdown

            if block.label == "SECTION_HEADER" and len(block_text) <= config.MAX_HEADER_CHARS:
                current_header = block_text
                continue

            prefix = ""
            if current_header and current_header != last_header:
                prefix = f"{current_header}:\n"

            is_over_sized = len(prefix) + len(block_text) > config.MAX_JINA_LARGE_CHUNK_CHARS
            if is_over_sized:
                self._process_oversized_block(block_text, prefix, tracker, bid)
                last_header = current_header
                continue

            self._process_regular_block(block_text, prefix, current_header, tracker, bid)
            last_header = current_header

        tracker.flush()

        return tracker.get_large_blocks(), tracker.get_char_map_list()

    # def _embed_large_blocks(self, blocks_reg):
    #     embeddings_dict = {}
    #     large_blocks, char_map_list = self._build_large_blocks(blocks_reg)
    #     for i, large_block in enumerate(large_blocks):
    #         char_map = char_map_list[i]
    #         tokens = self._tokenizer(
    #             large_block,
    #             return_tensors="pt",
    #             return_offsets_mapping=True,
    #             padding=True,
    #             truncation=True,
    #             max_length=8192
    #         )

    #         token_ids = tokens["input_ids"].to(self._device)
    #         padding_mask = tokens["attention_mask"].to(self._device)

    #         # Grab [0] because HF expects batched inputs, so batched outputs
    #         offsets = tokens["offsets"][0].tolist()

    #         with torch.no_grad():
    #             output = self._model(input_ids=token_ids, attention_mask=padding_mask)
    #             enriched_tokens = output.last_hidden_state[0]

    #         for bid in char_map:
    #             token_indices = []
    #             map_start_idx, map_end_idx = char_map[bid]
    #             for tok_idx, (tok_start_idx, tok_end_idx) in enumerate(offsets):

    #                 # skip special tokens like [CLS], [SEP], etc their offsets are (0,0)
    #                 if tok_start_idx == tok_end_idx == 0:
    #                     continue

    #                 if tok_end_idx > map_start_idx and map_end_idx > tok_start_idx:
    #                     token_indices.append(tok_idx)

    #             # Edge case should never really happen, we'll skip this block
    #             if not token_indices:
    #                 continue

    #             start_tok_idx = min(token_indices)
    #             end_tok_idx = max(token_indices) + 1

    #             token_embeddings = enriched_tokens[start_tok_idx:end_tok_idx, :]
    #             mean_embedding








