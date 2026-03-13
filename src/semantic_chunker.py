# Suppress logging
import logging
logging.disable(logging.INFO)

from config import *
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
            EMBEDDING_MODEL,
            trust_remote_code=True
        ).to(self._device)
        self._model.eval()

        self._tokenizer = AutoTokenizer.from_pretrained(
            EMBEDDING_MODEL,
            trust_remote_code=True
        )


    def _split_sentence(self, tracker, sentence):
        start_idx = 0
        while start_idx < len(sentence):
            spacer = " " if tracker.curr_len() > 0 else ""
            end_idx = start_idx + MAX_CHUNK_CHARS - tracker.curr_len() - len(spacer)

            if end_idx >= len(sentence):
                tracker.add_text(spacer + sentence[start_idx:])
                return

            ws_match = re.search(r'.*(\s)', sentence[start_idx:end_idx])
            if ws_match:
                last_ws_idx = start_idx + ws_match.start(1)
                next_text = spacer + sentence[start_idx:last_ws_idx]
                next_len = tracker.curr_len() + len(next_text)

                if next_len >=  MIN_CHUNK_CHARS:
                    tracker.add_text(next_text)
                    start_idx = last_ws_idx + 1
                else:
                    tracker.add_text(spacer + sentence[start_idx:end_idx])
                    start_idx = end_idx

            else:
                tracker.add_text(spacer + sentence[start_idx:end_idx])
                start_idx = end_idx
            tracker.flush()


    def _split_block(self, tracker, next_text):
        sentences = self._seg.segment(next_text)

        for sentence in sentences:
            spacer = " " if tracker.curr_len() > 0 else ""
            next_text = spacer + sentence
            next_len= len(next_text) + tracker.curr_len()
            if next_len <= MAX_CHUNK_CHARS:
                tracker.add_text(next_text)
            else:
                if tracker.curr_len() >= MIN_CHUNK_CHARS:
                    tracker.flush()
                    if len(sentence) <= MAX_CHUNK_CHARS:
                        tracker.add_text(sentence)
                    else:
                        self._split_sentence(tracker, sentence)
                else:
                    self._split_sentence(tracker, sentence)


    def _build_chunks(self, blocks_reg):
        tracker = ChunkTracker()
        last_chunk_was_header = False

        for bid in blocks_reg:
            block = blocks_reg[bid]
            block_text = block.markdown
            spacer = "\n\n" if tracker.curr_len() > 0 else ""
            next_text = spacer + block_text
            next_len = tracker.curr_len() + len(next_text)

            if block.label == "SECTION_HEADER" and len(block_text) <= MAX_HEADER_CHARS:
                if tracker.curr_len() >= MIN_CHUNK_CHARS:
                    tracker.flush()
                    tracker.add_text(block_text)
                elif last_chunk_was_header:
                    if tracker.curr_len() < MIN_CHUNK_CHARS:
                        tracker.add_text(next_text)
                    else:
                        if next_len <= MAX_HEADER_STACK_CHARS:
                            tracker.add_text(next_text)
                        else:
                            tracker.flush()
                            if len(block_text) <= MAX_CHUNK_CHARS:
                                tracker.add_text(block_text)
                            else:
                                self._split_block(tracker, block_text)

                else:
                    tracker.add_text(next_text)
                last_chunk_was_header = True

            else:
                last_chunk_was_header = False
                if next_len <= MAX_CHUNK_CHARS:
                    tracker.add_text(next_text)
                else:
                    if tracker.curr_len() >= MIN_CHUNK_CHARS:
                        tracker.flush()
                        if len(block_text) <= MAX_CHUNK_CHARS:
                            tracker.add_text(block_text)
                        else:
                            self._split_block(tracker, block_text)
                    else:

                        self._split_block(tracker, block_text)

        tracker.flush()
        return tracker.get_chunks()







    # def _split_sentence(self, tracker, sentence):
    #     start_idx = 0
    #     while start_idx < len(sentence):
    #         end_idx = start_idx + MAX_CHUNK_CHARS - tracker.curr_len()

    #         if end_idx >= len(sentence):
    #             chunk = sentence[start_idx:]
    #             return f"{chunk}"

    #         ws_match = re.search(r'.*(\s)', sentence[start_idx:end_idx])
    #         has_space_after_threshold = ws_match and ws_match.start(1) >= MIN_SPACE_SPLIT_THRESHOLD_CHARS
    #         if has_space_after_threshold:
    #             last_space_idx = start_idx + ws_match.start(1)
    #             chunk = sentence[start_idx:last_space_idx]
    #             start_idx = last_space_idx
    #         else:
    #             chunk = sentence[start_idx:end_idx]
    #             start_idx = end_idx

    #         sub_blocks.append(chunk)

    #     return ""





    # def _build_large_blocks(self, blocks_reg):
    #     tracker = LargeChunkTracker()
    #     current_header = ""
    #     last_header= ""

    #     # TODO: Handle table items better
    #     for bid in sorted(blocks_reg.keys()):
    #         block = blocks_reg[bid]
    #         block_text = block.markdown

    #         if block.label == "SECTION_HEADER" and len(block_text) <= MAX_HEADER_CHARS:
    #             current_header = block_text
    #             continue

    #         prefix = ""
    #         if current_header and current_header != last_header:
    #             prefix = f"{current_header}:\n"

    #         is_over_sized = len(prefix) + len(block_text) > MAX_JINA_LARGE_CHUNK_CHARS
    #         if is_over_sized:
    #             self._process_oversized_block(block_text, prefix, tracker, bid)
    #             last_header = current_header
    #             continue

    #         self._process_regular_block(block_text, prefix, current_header, tracker, bid)
    #         last_header = current_header

    #     tracker.flush()

    #     return tracker.get_large_blocks(), tracker.get_char_map_list()




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








