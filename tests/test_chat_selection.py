import unittest
from io import StringIO
from unittest.mock import AsyncMock, Mock, patch

from rich.console import Console

from axon.db.models import ChatSummary
from axon.llm.history import user_message
from axon.session.chat_handlers import ChatHandlers
from axon.ui.axon_ui import AxonUI
from axon.ui.views import Views


class ChatSelectionUITests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_menu_aligns_name_and_date_columns(self) -> None:
        ui = AxonUI.__new__(AxonUI)
        ui._select_menu = Mock()
        ui._select_menu.select_item = AsyncMock()
        chats = [
            ChatSummary("A", "created-a", "accessed-a"),
            ChatSummary("Long Name", "created-b", "accessed-b"),
        ]

        with patch(
            "axon.ui.axon_ui.format_timestamp",
            side_effect=lambda value: value,
        ):
            ui._select_menu.select_item.return_value = (
                "A          created-a  accessed-a"
            )
            selected_name = await ui.select_chat(chats)

        self.assertEqual(selected_name, "A")
        ui._select_menu.select_item.assert_awaited_once_with(
            [
                "A          created-a  accessed-a",
                "Long Name  created-b  accessed-b",
            ],
            header="Name       Created    Last Accessed",
        )


class ChatSelectionHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._handlers = ChatHandlers.__new__(ChatHandlers)
        self._handlers._chat_repository = Mock()
        self._handlers._llm = Mock()
        self._handlers._ui = Mock()
        self._handlers._ui.select_chat = AsyncMock()

    async def test_load_without_name_uses_selected_chat(self) -> None:
        chats = [ChatSummary("Research", "created", "accessed")]
        history = [user_message("Hello")]
        self._handlers._chat_repository.get_chat_summaries.return_value = chats
        self._handlers._ui.select_chat.return_value = "Research"
        self._handlers._chat_repository.get_chat.return_value = history

        await self._handlers.load_chat()

        self._handlers._ui.select_chat.assert_awaited_once_with(chats)
        self._handlers._chat_repository.get_chat.assert_called_once_with(
            "Research"
        )
        self._handlers._llm.set_history.assert_called_once_with(history)

    async def test_load_with_name_skips_selection_menu(self) -> None:
        history = [user_message("Hello")]
        self._handlers._chat_repository.get_chat.return_value = history

        await self._handlers.load_chat("Research")

        self._handlers._ui.select_chat.assert_not_awaited()
        self._handlers._chat_repository.get_chat.assert_called_once_with(
            "Research"
        )

    async def test_load_cancellation_preserves_current_history(self) -> None:
        chats = [ChatSummary("Research", "created", "accessed")]
        self._handlers._chat_repository.get_chat_summaries.return_value = chats
        self._handlers._ui.select_chat.return_value = None

        await self._handlers.load_chat()

        self._handlers._chat_repository.get_chat.assert_not_called()
        self._handlers._llm.set_history.assert_not_called()

    async def test_load_reports_when_no_chats_are_saved(self) -> None:
        self._handlers._chat_repository.get_chat_summaries.return_value = []

        await self._handlers.load_chat()

        self._handlers._ui.info.assert_called_once_with(
            "No saved chats found in the database."
        )
        self._handlers._ui.select_chat.assert_not_awaited()

    async def test_delete_without_name_deletes_selected_chat(self) -> None:
        chats = [ChatSummary("Research", "created", "accessed")]
        self._handlers._chat_repository.get_chat_summaries.return_value = chats
        self._handlers._ui.select_chat.return_value = "Research"
        self._handlers._chat_repository.delete_chat.return_value = True

        await self._handlers.delete_chat()

        self._handlers._ui.select_chat.assert_awaited_once_with(chats)
        self._handlers._chat_repository.delete_chat.assert_called_once_with(
            "Research"
        )

    def test_list_displays_chat_summaries(self) -> None:
        chats = [ChatSummary("Research", "created", "accessed")]
        self._handlers._chat_repository.get_chat_summaries.return_value = chats

        self._handlers.list_chats()

        self._handlers._ui.display_chats.assert_called_once_with(chats)


class ChatListViewTests(unittest.TestCase):
    def test_displays_chat_metadata_columns(self) -> None:
        console = Console(
            file=StringIO(),
            record=True,
            width=100,
            color_system=None,
        )
        views = Views(console)
        chats = [
            ChatSummary(
                "Research",
                "2026-08-10T12:00:00+00:00",
                "2026-08-11T15:30:00+00:00",
            )
        ]

        views.display_chats(chats)

        output = console.export_text()
        self.assertIn("Saved Chats", output)
        self.assertIn("Name", output)
        self.assertIn("Created", output)
        self.assertIn("Last Accessed", output)
        self.assertIn("Research", output)


if __name__ == "__main__":
    unittest.main()
