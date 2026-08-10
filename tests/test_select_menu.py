import unittest
from unittest.mock import AsyncMock, Mock

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from axon.ui.select_menu import SelectMenu


class SelectMenuTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._menu = SelectMenu.__new__(SelectMenu)
        self._menu._app = Mock()
        self._menu._app.run_async = AsyncMock(return_value="Second")
        self._menu._highlighted_idx = 0
        self._menu._items = []

    async def test_starts_on_selected_item(self) -> None:
        result = await self._menu.select_item(
            items=["First", "Second", "Third"],
            selected_item="Second",
        )

        self.assertEqual(result, "Second")
        self.assertEqual(self._menu._highlighted_idx, 1)

    async def test_starts_on_first_item_when_selection_is_unavailable(self) -> None:
        self._menu._highlighted_idx = 2

        await self._menu.select_item(
            items=["First", "Second", "Third"],
            selected_item="Missing",
        )

        self.assertEqual(self._menu._highlighted_idx, 0)

    def test_escape_cancels_selection_and_resets_menu_state(self) -> None:
        self._menu._kb = KeyBindings()
        self._menu._items = ["First", "Second"]
        self._menu._highlighted_idx = 1
        self._menu._bind_keys()
        event = Mock()
        escape_binding = next(
            binding
            for binding in self._menu._kb.bindings
            if binding.keys == (Keys.Escape,)
        )

        escape_binding.handler(event)

        self.assertEqual(self._menu._items, [])
        self.assertEqual(self._menu._highlighted_idx, 0)
        event.app.exit.assert_called_once_with(result=None)


if __name__ == "__main__":
    unittest.main()
