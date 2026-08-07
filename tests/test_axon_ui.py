import unittest
from unittest.mock import Mock

from axon.ui.axon_ui import AxonUI


class AxonUITests(unittest.TestCase):
    def setUp(self) -> None:
        self._ui = AxonUI.__new__(AxonUI)
        self._ui._console = Mock()
        self._ui._prompt = Mock()
        self._ui._suppress_next_prompt_newline = False

    def test_clear_screen_suppresses_only_the_next_prompt_newline(self) -> None:
        self._ui.clear_screen()

        self._ui.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self._ui._console.clear.assert_called_once_with()
        self._ui._console.print.assert_not_called()

        self._ui.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self._ui._console.print.assert_called_once_with()

    def test_listen_passes_model_name_to_prompt(self) -> None:
        self._ui.listen(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )

        self._ui._prompt.listen.assert_called_once_with(
            curr_tokens=10,
            context_size=100,
            model_name="gemini-test",
        )


if __name__ == "__main__":
    unittest.main()
