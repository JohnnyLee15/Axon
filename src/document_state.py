from types import SimpleNamespace
from typing import TypeAlias

Block: TypeAlias = SimpleNamespace

class DocumentState:
    def __init__(self) -> None:
        self._blocks_reg = {}
        self._curr_bid = 0
        self._seen_content = set()
        self._full_raw_text = ""
        self._page1 = ""
        self._title = None

    def add_block(self, markdown: str, label: str, page_no: int, is_noise_risk: bool) -> None:
        spacer_full = "" if not self._full_raw_text else "\n\n"
        self._full_raw_text += (spacer_full + markdown)

        if page_no == 1:
            spacer_first = "" if not self._page1 else "\n\n"
            self._page1 += (spacer_first + markdown)

            if label == "TITLE" and self._title is None:
                self._title = markdown.lstrip("#").strip().lower()

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

    def get_doc_state(self) -> tuple[dict[int, Block], str, str, str | None]:
        return self._blocks_reg, self._full_raw_text, self._page1, self._title
