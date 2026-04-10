from types import SimpleNamespace
from typing import TypeAlias

Block: TypeAlias = SimpleNamespace
ParsedDoc: TypeAlias = SimpleNamespace

class DocumentState:
    def __init__(self) -> None:
        self._blocks_reg = {}
        self._curr_bid = 0
        self._seen_content = set()
        self._full_raw_text = ""
        self._page_one = ""
        self._title = None


    def add_block(self, markdown: str, label: str, is_noise_risk: bool) -> None:
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


    def set_title_if_missing(self, text: str) -> None:
        if not self._title:
            self._title = text


    def add_to_full_raw_text(self, text: str) -> None:
        spacer_full = "" if not self._full_raw_text else "\n\n"
        self._full_raw_text += (spacer_full + text)


    def add_to_first_page(self, text: str) -> None:
        spacer_first = "" if not self._page_one else "\n\n"
        self._page_one += (spacer_first + text)


    def get_doc_state(self) -> ParsedDoc:
        return ParsedDoc(
            blocks_reg = self._blocks_reg,
            full_raw_text = self._full_raw_text,
            page_one = self._page_one,
            title = self._title,
            doi = None,
            pmcid = None,
            pmid = None,
            arxiv = None
        )
