import config
import torch
import pysbd
from transformers import AutoModel
from parsed_block import ParsedBlock
import re

class SemanticChunker:
    def __init__(self):
        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        self.device = torch.device("mps")
        self.seg = pysbd.Segmenter(language="en", clean=False)
        self.model = AutoModel.from_pretrained(
            config.EMBEDDING_MODEL,
            trust_remote_code=True
        ).to(self.device)
        self.model.eval()


    def _split_oversized_block(self, text, prefix):
        sentences = self.seg.segment(text)
        sub_blocks = []
        current_sub = prefix

        for sentence in sentences:
            if len(sentence) > config.MAX_JINA_LARGE_CHUNK_CHARS:
                start_idx = 0

                while start_idx < len(sentence):
                    end_idx = start_idx + config.MAX_JINA_LARGE_CHUNK_CHARS - len(prefix)

                    if end_idx >= len(sentence):
                        chunk = sentence[start_idx:]
                        current_sub = f"{prefix}{chunk}"
                        break

                    white_space_match = re.search(r'.*(\s)', sentence[start_idx:end_idx])
                    if white_space_match and white_space_match.start(1) >= config.MIN_SPACE_SPLIT_THRESHOLD_CHARS:
                        last_space_idx = start_idx + white_space_match.start(1)
                        chunk = sentence[start_idx:last_space_idx]
                        start_idx = last_space_idx
                    else:
                        chunk = sentence[start_idx:end_idx]
                        start_idx = end_idx

                    sub_blocks.append(f"{prefix}{chunk}")
                continue

            spacer = " " if current_sub != prefix else ""
            if len(current_sub) + len(spacer) + len(sentence) > config.MAX_JINA_LARGE_CHUNK_CHARS:
                sub_blocks.append(current_sub)

                current_sub = f"{prefix}{sentence}"
            else:
                current_sub += f"{spacer}{sentence}"

        if current_sub and current_sub != prefix:
            sub_blocks.append(current_sub)

        return sub_blocks

    def _build_large_blocks(self, blocks_reg):
        large_blocks = []
        current_large_block = ""
        current_header = ""
        last_header= ""

        for bid in sorted(blocks_reg.keys()):
            block = blocks_reg[bid]
            block_text = block.text

            if block.label == "SECTION_HEADER":
                current_header = block_text
                continue

            prefix = ""
            if current_header and current_header != last_header:
                prefix = f"{current_header}:\n"

            if len(prefix) + len(block_text) > config.MAX_JINA_LARGE_CHUNK_CHARS:
                sub_chunks = self._split_oversized_block(block_text, prefix)

                if sub_chunks:
                    spacer = "\n\n" if current_large_block else ""
                    if len(current_large_block) + len(spacer) + len(sub_chunks[0]) <= config.MAX_JINA_LARGE_CHUNK_CHARS:
                        current_large_block += f"{spacer}{sub_chunks.pop(0)}"

                    if current_large_block:
                        large_blocks.append(current_large_block)
                        current_large_block = ""

                    if len(sub_chunks) > 1:
                        large_blocks.extend(sub_chunks[:-1])

                    if sub_chunks:
                        current_large_block = sub_chunks[-1]

                last_header = current_header
                continue

            full_entry = f"{prefix}{block_text}"
            spacer = "\n\n" if current_large_block else ""

            if len(current_large_block) + len(spacer) + len(full_entry) > config.MAX_JINA_LARGE_CHUNK_CHARS:
                if current_large_block:
                    large_blocks.append(current_large_block)

                current_large_block = f"{current_header}:\n{block_text}" if current_header else block_text
            else:
                current_large_block += f"{spacer}{full_entry}"

            last_header = current_header

        if current_large_block:
            large_blocks.append(current_large_block)

        return large_blocks
