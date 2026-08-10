import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from axon.ui.input_session import InputSession


class InputSessionTests(unittest.IsolatedAsyncioTestCase):
    def test_ctrl_j_is_bound_to_multiline_input(self) -> None:
        session = InputSession.__new__(InputSession)
        session._key_bindings = KeyBindings()

        session._bind_keys()

        key_sequences = {
            binding.keys
            for binding in session._key_bindings.bindings
        }
        self.assertIn((Keys.ControlJ,), key_sequences)
        self.assertNotIn((Keys.Escape, Keys.ControlM), key_sequences)

    def test_user_input_height_uses_wrapped_window_height_and_padding(self) -> None:
        session = InputSession.__new__(InputSession)
        session._input_window = Mock()
        session._input_window.preferred_height.return_value = SimpleNamespace(
            preferred=4,
        )

        with patch("axon.ui.input_session.get_app") as get_app:
            get_app.return_value.output.get_size.return_value = SimpleNamespace(
                rows=30,
                columns=80,
            )

            height = session._get_user_input_height()

        self.assertEqual(height, 6)
        session._input_window.preferred_height.assert_called_once_with(
            width=80,
            max_available_height=27,
        )

    async def test_prompt_updates_status_text_before_running_application(self) -> None:
        session = InputSession.__new__(InputSession)
        session._buffer = Mock()
        session._application = Mock()
        session._application.run_async = AsyncMock(return_value="hello")

        result = await session.prompt(
            prompt_text="[You] > ",
            status_text="  gemini-test  •  ~/Axon",
        )

        self.assertEqual(result, "hello")
        self.assertEqual(session._get_status_text(), "  gemini-test  •  ~/Axon")
        session._buffer.reset.assert_called_once_with()
        session._application.run_async.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
