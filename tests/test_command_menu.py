import unittest
from types import SimpleNamespace
from unittest.mock import patch

from prompt_toolkit.completion import Completion

from axon.ui.command_menu import CommandMenuControl, MAX_VISIBLE_COMMANDS


CURRENT_STYLE = "class:command-menu.item.current"
DEFAULT_STYLE = "class:command-menu.item"
CURRENT_DESCRIPTION_STYLE = "class:command-menu.description.current"
DEFAULT_DESCRIPTION_STYLE = "class:command-menu.description"


class CommandMenuControlTests(unittest.TestCase):
    def _completion_state(
        self,
        count: int,
        selected_index: int | None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            completions=[
                Completion(
                    text=f"/command-{index}",
                    display_meta=f"Description {index}",
                )
                for index in range(count)
            ],
            complete_index=selected_index,
        )

    def _app_with_state(self, state: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(
            current_buffer=SimpleNamespace(complete_state=state),
        )

    def test_highlights_first_completion_before_selection(self) -> None:
        state = self._completion_state(count=3, selected_index=None)
        control = CommandMenuControl()

        with patch(
            "axon.ui.command_menu.get_app",
            return_value=self._app_with_state(state),
        ):
            content = control.create_content(80, MAX_VISIBLE_COMMANDS)

        self.assertEqual(content.line_count, 3)
        self.assertEqual(
            content.get_line(0),
            [
                (CURRENT_STYLE, "/command-0"),
                (CURRENT_DESCRIPTION_STYLE, "  Description 0"),
            ],
        )
        self.assertEqual(
            content.get_line(1),
            [
                (DEFAULT_STYLE, "/command-1"),
                (DEFAULT_DESCRIPTION_STYLE, "  Description 1"),
            ],
        )

    def test_scrolls_to_keep_selected_completion_visible(self) -> None:
        state = self._completion_state(count=10, selected_index=8)
        control = CommandMenuControl()

        with patch(
            "axon.ui.command_menu.get_app",
            return_value=self._app_with_state(state),
        ):
            content = control.create_content(80, MAX_VISIBLE_COMMANDS)

        self.assertEqual(content.line_count, MAX_VISIBLE_COMMANDS)
        self.assertEqual(
            content.get_line(0),
            [
                (DEFAULT_STYLE, "/command-1"),
                (DEFAULT_DESCRIPTION_STYLE, "  Description 1"),
            ],
        )
        self.assertEqual(
            content.get_line(7),
            [
                (CURRENT_STYLE, "/command-8"),
                (CURRENT_DESCRIPTION_STYLE, "  Description 8"),
            ],
        )

    def test_preferred_height_respects_terminal_space(self) -> None:
        state = self._completion_state(count=10, selected_index=0)
        control = CommandMenuControl()

        with patch(
            "axon.ui.command_menu.get_app",
            return_value=self._app_with_state(state),
        ):
            height = control.preferred_height(
                80,
                5,
                False,
                None,
            )

        self.assertEqual(height, 5)

    def test_displays_completion_label_instead_of_inserted_suffix(self) -> None:
        state = SimpleNamespace(
            completions=[
                Completion(
                    text="pers",
                    display="papers/",
                )
            ],
            complete_index=None,
        )
        control = CommandMenuControl()

        with patch(
            "axon.ui.command_menu.get_app",
            return_value=self._app_with_state(state),
        ):
            content = control.create_content(80, MAX_VISIBLE_COMMANDS)

        self.assertEqual(
            content.get_line(0),
            [
                (CURRENT_STYLE, "papers/"),
                (CURRENT_DESCRIPTION_STYLE, "  "),
            ],
        )


if __name__ == "__main__":
    unittest.main()
