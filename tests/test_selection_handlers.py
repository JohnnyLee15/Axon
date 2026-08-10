import unittest
from unittest.mock import Mock

from axon.config.settings_store import CHAT_LIMIT_KEY, CHAT_MODEL_KEY
from axon.session.chat_handlers import ChatHandlers
from axon.session.manager import SessionManager


class SelectionHandlerTests(unittest.TestCase):
    def test_model_selection_cancellation_preserves_current_model(self) -> None:
        manager = SessionManager.__new__(SessionManager)
        manager._ui = Mock()
        manager._llm = Mock()
        manager._settings = Mock()
        manager._llm.get_chat_model.return_value = "model-a"
        manager._ui.select_item.return_value = None

        manager._select_model()

        manager._llm.set_chat_model.assert_not_called()
        manager._settings.set.assert_not_called()
        manager._ui.info.assert_not_called()

    def test_model_selection_updates_model_and_persists_setting(self) -> None:
        manager = SessionManager.__new__(SessionManager)
        manager._ui = Mock()
        manager._llm = Mock()
        manager._settings = Mock()
        manager._llm.get_chat_model.return_value = "model-a"
        manager._ui.select_item.return_value = "model-b"

        manager._select_model()

        manager._llm.set_chat_model.assert_called_once_with("model-b")
        manager._settings.set.assert_called_once_with(
            key=CHAT_MODEL_KEY,
            value="model-b",
        )

    def test_chat_limit_selection_cancellation_preserves_current_limit(self) -> None:
        handlers = ChatHandlers.__new__(ChatHandlers)
        handlers._ui = Mock()
        handlers._llm = Mock()
        handlers._settings = Mock()
        handlers._llm.get_chat_limit.return_value = 100_000
        handlers._ui.select_item.return_value = None

        handlers.set_limit()

        handlers._llm.set_chat_limit.assert_not_called()
        handlers._settings.set.assert_not_called()
        handlers._ui.info.assert_not_called()

    def test_chat_limit_selection_updates_limit_and_persists_setting(self) -> None:
        handlers = ChatHandlers.__new__(ChatHandlers)
        handlers._ui = Mock()
        handlers._llm = Mock()
        handlers._settings = Mock()
        handlers._llm.get_chat_limit.return_value = 100_000
        handlers._ui.select_item.return_value = 200_000

        handlers.set_limit()

        handlers._llm.set_chat_limit.assert_called_once_with(200_000)
        handlers._settings.set.assert_called_once_with(
            key=CHAT_LIMIT_KEY,
            value=200_000,
        )


if __name__ == "__main__":
    unittest.main()
