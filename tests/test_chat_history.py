import unittest
from io import StringIO
from unittest.mock import Mock

from rich.console import Console

from axon.commands.contracts import COMMAND_HANDLER_NAMES
from axon.commands.processor import CommandProcessor
from axon.commands.registry import COMMANDS
from axon.llm.history import model_message, tool_call, tool_response, user_message
from axon.session.chat_handlers import ChatHandlers
from axon.ui.views import Views


class ChatHistoryHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._handlers = ChatHandlers.__new__(ChatHandlers)
        self._handlers._llm = Mock()
        self._handlers._ui = Mock()

    def test_reports_when_no_history_is_retained(self) -> None:
        self._handlers._llm.get_history.return_value = []

        self._handlers.display_history()

        self._handlers._ui.info.assert_called_once_with(
            "No chat history is currently retained."
        )
        self._handlers._ui.display_history.assert_not_called()

    def test_forwards_retained_history_to_ui(self) -> None:
        history = [user_message("Hello"), model_message("Hi there")]
        self._handlers._llm.get_history.return_value = history

        self._handlers.display_history()

        self._handlers._ui.display_history.assert_called_once_with(history)
        self._handlers._ui.info.assert_not_called()


class ChatHistoryViewTests(unittest.TestCase):
    def test_renders_text_and_tool_events(self) -> None:
        console = Console(
            file=StringIO(),
            record=True,
            width=100,
            color_system=None,
        )
        views = Views(console)
        history = [
            user_message("Find the **paper**."),
            tool_call("search_library", {"query": "the paper"}),
            tool_response("search_library", "One result found."),
            model_message("I found it."),
        ]

        views.display_history(history)

        output = console.export_text()
        self.assertIn("Chat History", output)
        self.assertIn("[You] > Find the paper.", output)
        self.assertIn("[Tool] search_library", output)
        self.assertIn("  query: the paper", output)
        self.assertIn("[Result] search_library", output)
        self.assertIn("  One result found.", output)
        self.assertIn("[Axon] > I found it.", output)


class ChatHistoryCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_history_routes_to_registered_handler(self) -> None:
        handler = Mock()
        processor = CommandProcessor(
            commands=COMMANDS,
            handlers={COMMAND_HANDLER_NAMES.DISPLAY_HISTORY: handler},
            ui=Mock(),
        )

        should_exit = await processor.process("/chat history")

        handler.assert_called_once_with()
        self.assertFalse(should_exit)


if __name__ == "__main__":
    unittest.main()
