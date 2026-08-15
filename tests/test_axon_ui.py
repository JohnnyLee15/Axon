import unittest
from unittest.mock import AsyncMock, Mock

from axon.ui.axon_ui import AxonUI
from axon.ui.wait_status import DEFAULT_WAIT_LABEL


class AxonUITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._ui = AxonUI.__new__(AxonUI)
        self._ui._console = Mock()
        self._ui._prompt = Mock()
        self._ui._prompt.listen = AsyncMock()
        self._ui._prompt.stream_response = AsyncMock()
        self._ui._select_menu = Mock()
        self._ui._select_menu.select_item = AsyncMock()
        self._ui._suppress_next_prompt_newline = False

    async def test_clear_screen_suppresses_only_the_next_prompt_newline(self) -> None:
        self._ui.clear_screen()

        await self._ui.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self._ui._prompt.clear_screen.assert_called_once_with()
        self._ui._console.print.assert_not_called()

        await self._ui.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self._ui._console.print.assert_called_once_with()

    async def test_listen_passes_model_name_to_prompt(self) -> None:
        await self._ui.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self._ui._prompt.listen.assert_awaited_once_with(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

    def test_wait_forwards_cancel_hint_to_prompt(self) -> None:
        self._ui.wait(
            show_cancel_hint=True,
            started_at=100.0,
        )

        self._ui._prompt.wait.assert_called_once_with(
            show_cancel_hint=True,
            started_at=100.0,
            label=DEFAULT_WAIT_LABEL,
        )

    def test_wait_forwards_custom_label_to_prompt(self) -> None:
        self._ui.wait(label="Downloading model")

        self._ui._prompt.wait.assert_called_once_with(
            show_cancel_hint=False,
            started_at=None,
            label="Downloading model",
        )

    async def test_stream_response_forwards_stream_and_start_time(self) -> None:
        async def response_stream():
            yield "response"

        stream = response_stream()
        self._ui._prompt.stream_response.return_value = "response"

        response = await self._ui.stream_response(
            response_stream=stream,
            started_at=100.0,
        )

        self.assertEqual(response, "response")
        self._ui._prompt.stream_response.assert_awaited_once_with(
            response_stream=stream,
            started_at=100.0,
        )

    def test_display_response_delegates_to_prompt(self) -> None:
        self._ui.display_response("complete response")

        self._ui._prompt.display_response.assert_called_once_with(
            "complete response"
        )

    async def test_select_item_maps_string_option_to_display_and_back(self) -> None:
        options = [
            {"option": "model-a", "desc": "fast"},
            {"option": "model-b", "desc": "accurate"},
        ]
        self._ui._select_menu.select_item.return_value = "model-b"

        selected_option = await self._ui.select_item(
            options=options,
            selected_option="model-a",
        )

        self.assertEqual(selected_option, "model-b")
        self._ui._select_menu.select_item.assert_awaited_once_with(
            ["model-a", "model-b"],
            descriptions=["fast", "accurate"],
            selected_item="model-a",
        )

    async def test_select_item_formats_integer_options_and_maps_them_back(self) -> None:
        options = [
            {"option": 10_000, "desc": "small"},
            {"option": 20_000, "desc": "short"},
        ]
        self._ui._select_menu.select_item.return_value = "20,000"

        selected_option = await self._ui.select_item(
            options=options,
            selected_option=10_000,
        )

        self.assertEqual(selected_option, 20_000)
        self._ui._select_menu.select_item.assert_awaited_once_with(
            ["10,000", "20,000"],
            descriptions=["small", "short"],
            selected_item="10,000",
        )

    async def test_select_item_returns_none_when_menu_is_canceled(self) -> None:
        options = [
            {"option": "model-a", "desc": "fast"},
            {"option": "model-b", "desc": "accurate"},
        ]
        self._ui._select_menu.select_item.return_value = None

        selected_option = await self._ui.select_item(
            options=options,
            selected_option="model-a",
        )

        self.assertIsNone(selected_option)


class AxonUIAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_interrupt_delegates_to_interrupt_listener(self) -> None:
        ui = AxonUI.__new__(AxonUI)
        ui._interrupt_listener = Mock()
        ui._interrupt_listener.wait = AsyncMock()

        await ui.wait_for_interrupt()

        ui._interrupt_listener.wait.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
