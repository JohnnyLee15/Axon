import sqlite3

from axon.db.paper_repository import PaperRepository
from axon.ingestion.ingestion_runner import IngestionRunner
from axon.ui.axon_ui import AxonUI
from axon.ui.formatters import emphasis
from axon.ui.choices import CONFIRM_YES, CONFIRM_NO


class LibraryHandlers:
    def __init__(
        self,
        paper_repository: PaperRepository,
        ingestion_runner: IngestionRunner,
        ui: AxonUI
    ) -> None:
        self._paper_repository = paper_repository
        self._ingestion_runner = ingestion_runner
        self._ui = ui


    def clear_library(self) -> None:
        self._ui.warning("This will permanently delete ALL papers from the database.")

        options = f"{CONFIRM_YES}/{CONFIRM_NO}"
        confirm = self._ui.confirm(f"Are you sure? ({emphasis(options)})").strip().lower()
        if confirm != CONFIRM_YES:
            self._ui.info("Library clear canceled.")
            return

        try:
            self._paper_repository.delete_all_papers()
        except sqlite3.Error as e:
            self._ui.error(f"Could not delete saved papers: {e}")
            return

        self._ui.success("Library cleared successfully!")


    def load_pdfs(self, filepath: str) -> None:
        self._ingestion_runner.load_pdfs(filepath)
