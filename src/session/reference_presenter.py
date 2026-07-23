import sqlite3

from src.db.paper_repository import PaperRepository
from src.ui.axon_ui import AxonUI


class ReferencePresenter:
    def __init__(self, paper_repository: PaperRepository, ui: AxonUI) -> None:
        self._paper_repository = paper_repository
        self._ui = ui


    def display_references(self, chunks: dict[int, dict[str, str | int]]) -> None:
        if not chunks:
            return

        paper_ids = {chunk["paper_id"] for chunk in chunks.values()}

        try:
            paper_properties = self._paper_repository.get_metadata_by_ids(list(paper_ids))
        except sqlite3.Error as e:
            self._ui.error(f"Could not retrieve paper references: {e}")
            return

        if not paper_properties:
            return

        self._ui.display_references(paper_properties)
