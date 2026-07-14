from src.db.vector_database import VectorDatabase
from src.session.ingestion_runner import IngestionRunner
from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis
from src.commands.choices import CONFIRM_YES, CONFIRM_NO


class DatabaseHandlers:
    def __init__(
        self,
        db: VectorDatabase,
        ingestion_runner: IngestionRunner,
        ui: AxonUI
    ) -> None:
        self._db = db
        self._ingestion_runner = ingestion_runner
        self._ui = ui


    def clear_db(self) -> None:
        self._ui.warning(
            "This will permanently delete ALL papers, chunks, "
            "embeddings, and saved chats"
        )

        options = f"{CONFIRM_YES}/{CONFIRM_NO}"
        confirm = self._ui.confirm(f"Are you sure? ({emphasis(options)}): ").strip().lower()
        if confirm == CONFIRM_YES:
            self._db.reset()
            self._ui.success("Vector database completely cleared!")
        else:
            self._ui.info("Database clear canceled.")


    def load_pdfs(self, filepath: str) -> None:
        self._ingestion_runner.load_pdfs(filepath)
