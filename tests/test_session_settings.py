import unittest
from unittest.mock import Mock, patch

from axon.config.settings_store import CHAT_LIMIT_KEY, CHAT_MODEL_KEY
from axon.llm.models import DEFAULT_CHAT_MODEL, GEMINI_3_1_FLASH_LITE
from axon.llm.settings import DEFAULT_CONTEXT_SIZE
from axon.session import manager as manager_module
from axon.session.manager import SessionManager


class SessionSettingsTests(unittest.TestCase):
    def _construct_manager(self, settings: Mock) -> tuple[Mock, Mock, Mock]:
        ui = Mock()
        llm_adapter = Mock()

        with (
            patch.object(manager_module, "ChatLLM") as chat_llm,
            patch.object(SessionManager, "_init_database"),
            patch.object(SessionManager, "_init_ingestion"),
            patch.object(SessionManager, "_init_session_services"),
            patch.object(SessionManager, "_init_command_processor"),
        ):
            SessionManager(
                ui=ui,
                llm_adapter=llm_adapter,
                settings=settings,
            )

        return chat_llm, ui, llm_adapter

    def test_restores_saved_model_and_chat_limit(self) -> None:
        saved_values = {
            CHAT_MODEL_KEY: GEMINI_3_1_FLASH_LITE,
            CHAT_LIMIT_KEY: 100_000,
        }
        settings = Mock()
        settings.get.side_effect = saved_values.get

        chat_llm, ui, llm_adapter = self._construct_manager(settings)

        chat_llm.assert_called_once_with(
            ui=ui,
            llm_adapter=llm_adapter,
            chat_model=GEMINI_3_1_FLASH_LITE,
            context_size=100_000,
        )

    def test_uses_defaults_when_saved_settings_are_missing(self) -> None:
        settings = Mock()
        settings.get.return_value = None

        chat_llm, ui, llm_adapter = self._construct_manager(settings)

        chat_llm.assert_called_once_with(
            ui=ui,
            llm_adapter=llm_adapter,
            chat_model=DEFAULT_CHAT_MODEL,
            context_size=DEFAULT_CONTEXT_SIZE,
        )

    def test_invalid_saved_model_falls_back_without_discarding_valid_limit(self) -> None:
        saved_values = {
            CHAT_MODEL_KEY: "unavailable-model",
            CHAT_LIMIT_KEY: 100_000,
        }
        settings = Mock()
        settings.get.side_effect = saved_values.get

        chat_llm, ui, llm_adapter = self._construct_manager(settings)

        chat_llm.assert_called_once_with(
            ui=ui,
            llm_adapter=llm_adapter,
            chat_model=DEFAULT_CHAT_MODEL,
            context_size=100_000,
        )

    def test_invalid_saved_limit_falls_back_without_discarding_valid_model(self) -> None:
        saved_values = {
            CHAT_MODEL_KEY: GEMINI_3_1_FLASH_LITE,
            CHAT_LIMIT_KEY: 123_456,
        }
        settings = Mock()
        settings.get.side_effect = saved_values.get

        chat_llm, ui, llm_adapter = self._construct_manager(settings)

        chat_llm.assert_called_once_with(
            ui=ui,
            llm_adapter=llm_adapter,
            chat_model=GEMINI_3_1_FLASH_LITE,
            context_size=DEFAULT_CONTEXT_SIZE,
        )


if __name__ == "__main__":
    unittest.main()
