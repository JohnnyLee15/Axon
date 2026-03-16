from types import SimpleNamespace
from typing import TypeAlias

Block: TypeAlias = SimpleNamespace

class BlockTracker:
    def __init__(self) -> None:
        self._blocks_reg = {}
        self._curr_bid = 0
        self._seen_content = set()

    def add_block(self, markdown: str,label: str, is_noise_risk: bool) -> None:
        content_hash = hash(markdown)
        if content_hash in self._seen_content:
            return

        self._seen_content.add(content_hash)
        self._blocks_reg[self._curr_bid] = Block(
            markdown = markdown,
            label = label,
            is_noise_risk = is_noise_risk
        )
        self._curr_bid += 1

    def get_blocks_reg(self) -> dict[int, Block]:
        return self._blocks_reg
