import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from axon.ui.input_session import InputSession


class InputSessionTests(unittest.TestCase):
    def test_user_input_height_includes_vertical_padding(self) -> None:
        session = InputSession.__new__(InputSession)
        session._buffer = SimpleNamespace(
            document=SimpleNamespace(line_count=1),
        )

        self.assertEqual(session._get_user_input_height(), 3)

        session._buffer.document.line_count = 3

        self.assertEqual(session._get_user_input_height(), 5)

    def test_prompt_updates_status_text_before_running_application(self) -> None:
        session = InputSession.__new__(InputSession)
        session._buffer = Mock()
        session._application = Mock()
        session._application.run.return_value = "hello"

        result = session.prompt(
            prompt_text="[You] > ",
            status_text="  gemini-test  •  ~/Axon",
        )

        self.assertEqual(result, "hello")
        self.assertEqual(session._get_status_text(), "  gemini-test  •  ~/Axon")
        session._buffer.reset.assert_called_once_with()
        session._application.run.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
