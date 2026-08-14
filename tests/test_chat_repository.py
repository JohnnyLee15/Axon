import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from axon.db.chat_repository import ChatRepository
from axon.db.contracts import CHAT_FIELDS
from axon.db.schema_manager import CHAT_TABLE, SchemaManager
from axon.db.sqlite_database import SQLiteDatabase
from axon.llm.history import user_message


class ChatRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "test.db"
        self._database = SQLiteDatabase(database_path)
        SchemaManager(self._database).initialize()
        self._repository = ChatRepository(self._database)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_loading_chat_updates_access_time_without_changing_creation(self) -> None:
        created_at = "2026-08-10T12:00:00+00:00"
        accessed_at = "2026-08-11T15:30:00+00:00"
        history = [user_message("Hello")]

        with patch(
            "axon.db.chat_repository._utc_now",
            side_effect=[created_at, accessed_at],
        ):
            self._repository.insert_chat("Research", history)
            loaded_history = self._repository.get_chat("Research")

        summaries = self._repository.get_chat_summaries()

        self.assertEqual(loaded_history, history)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0][CHAT_FIELDS.NAME], "Research")
        self.assertEqual(summaries[0][CHAT_FIELDS.CREATED_AT], created_at)
        self.assertEqual(
            summaries[0][CHAT_FIELDS.LAST_ACCESSED_AT],
            accessed_at,
        )

    def test_overwrite_preserves_creation_and_updates_access_time(self) -> None:
        original_time = "2026-08-10T12:00:00+00:00"
        overwrite_time = "2026-08-12T12:00:00+00:00"

        with patch(
            "axon.db.chat_repository._utc_now",
            side_effect=[original_time, overwrite_time],
        ):
            self._repository.insert_chat("Research", [user_message("Old")])
            self._repository.insert_chat(
                "Research",
                [user_message("New")],
                overwrite=True,
            )

        summary = self._repository.get_chat_summaries()[0]
        with self._database.connect() as connection:
            content = connection.execute(
                f"SELECT chat_content FROM {CHAT_TABLE} WHERE name = ?;",
                ("Research",),
            ).fetchone()[0]

        self.assertIn("New", content)
        self.assertEqual(summary[CHAT_FIELDS.CREATED_AT], original_time)
        self.assertEqual(
            summary[CHAT_FIELDS.LAST_ACCESSED_AT],
            overwrite_time,
        )


if __name__ == "__main__":
    unittest.main()
