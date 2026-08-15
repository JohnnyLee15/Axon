import sqlite3

from axon.db.paper_repository import PaperRepository
from axon.db.contracts import CHUNK_FIELDS
from axon.ui.axon_ui import AxonUI
from axon.web_search.contracts import WEB_SOURCE_FIELDS


class ReferencePresenter:
    def __init__(self, paper_repository: PaperRepository, ui: AxonUI) -> None:
        self._paper_repository = paper_repository
        self._ui = ui


    def display_references(self, chunks: dict[int, dict[str, str | int]]) -> None:
        if not chunks:
            return

        paper_ids = {chunk[CHUNK_FIELDS.PAPER_ID] for chunk in chunks.values()}

        try:
            paper_properties = self._paper_repository.get_metadata_by_ids(list(paper_ids))
        except sqlite3.Error as e:
            self._ui.error(f"Could not retrieve paper references: {e}")
            return

        if not paper_properties:
            return

        self._ui.display_references(paper_properties)


    def display_web_sources(self, sources: list[dict[str, str]]) -> None:
        unique_sources = []
        seen_urls = set()

        for source in sources:
            url = source[WEB_SOURCE_FIELDS.URL]
            if url in seen_urls:
                continue

            seen_urls.add(url)
            unique_sources.append(source)

        if unique_sources:
            self._ui.display_web_sources(unique_sources)
