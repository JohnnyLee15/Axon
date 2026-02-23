import config
import torch
from transformers import AutoModel
from parsed_block import ParsedBlock

class SemanticChunker:
    def __init__(self):
        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        self.device = torch.device("mps")

        self.model = AutoModel.from_pretrained(
            config.EMBEDDING_MODEL,
            trust_remote_code=True
        ).to(self.device)

        self.model.eval()

    def _split_oversize_block():
        pass

    def _build_large_blocks(self, blocks_reg):
        large_blocks = []
        current_large_block = ""
        current_header = ""
        last_header= ""

        for bid in sorted(blocks_reg.keys()):
            block = blocks_reg[bid]
            block_text = block.text.strip()

            if block.label == "SECTION_HEADER":
                current_header += f"{block_text}:\n"
                continue

            prefix = ""
            if current_header and current_header != last_header:
                prefix = f"{current_header}:\n"

            if len(prefix) + len(block_text) > config.MAX_JINA_LARGE_CHUNK_CHARS:
                pass