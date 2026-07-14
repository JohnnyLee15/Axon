from src.db.vector_database import VectorDatabase
from src.ui.axon_ui import AxonUI


class ReferencePresenter:
    def __init__(self, db: VectorDatabase, ui: AxonUI) -> None:
        self._db = db
        self._ui = ui


    def display_references(self, chunks: dict[int, dict[str, str | int]]) -> None:
        if not chunks:
            return

        paper_ids = {chunk["paper_id"] for chunk in chunks.values()}
        paper_properties = self._db.get_paper_metadata_by_id(list(paper_ids))
        if not paper_properties:
            return

        self._ui.display_references(paper_properties)
