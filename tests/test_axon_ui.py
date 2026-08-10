import unittest
from unittest.mock import AsyncMock, Mock

from axon.ui.axon_ui import AxonUI


class AxonUITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._ui = AxonUI.__new__(AxonUI)
        self._ui._console = Mock()
        self._ui._prompt = Mock()
        self._ui._prompt.listen = AsyncMock()
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

        self._ui._console.clear.assert_called_once_with()
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
        )

    async def test_select_item_maps_string_id_to_label_and_back(self) -> None:
        options = [
            {"id": "model-a", "label": "Model A"},
            {"id": "model-b", "label": "Model B"},
        ]
        self._ui._select_menu.select_item.return_value = "Model B"

        selected_id = await self._ui.select_item(
            options=options,
            selected_id="model-a",
        )

        self.assertEqual(selected_id, "model-b")
        self._ui._select_menu.select_item.assert_awaited_once_with(
            ["Model A", "Model B"],
            selected_item="Model A",
        )

    async def test_select_item_maps_integer_id_to_label_and_back(self) -> None:
        options = [
            {"id": 10_000, "label": "10,000"},
            {"id": 20_000, "label": "20,000"},
        ]
        self._ui._select_menu.select_item.return_value = "20,000"

        selected_id = await self._ui.select_item(
            options=options,
            selected_id=10_000,
        )

        self.assertEqual(selected_id, 20_000)
        self._ui._select_menu.select_item.assert_awaited_once_with(
            ["10,000", "20,000"],
            selected_item="10,000",
        )

    async def test_select_item_returns_none_when_menu_is_canceled(self) -> None:
        options = [
            {"id": "model-a", "label": "Model A"},
            {"id": "model-b", "label": "Model B"},
        ]
        self._ui._select_menu.select_item.return_value = None

        selected_id = await self._ui.select_item(
            options=options,
            selected_id="model-a",
        )

        self.assertIsNone(selected_id)


class AxonUIAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_interrupt_delegates_to_interrupt_listener(self) -> None:
        ui = AxonUI.__new__(AxonUI)
        ui._interrupt_listener = Mock()
        ui._interrupt_listener.wait = AsyncMock()

        await ui.wait_for_interrupt()

        ui._interrupt_listener.wait.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
