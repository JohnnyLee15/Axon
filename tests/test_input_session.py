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
        self.assertIn((Keys.ControlI,), key_sequences)
        self.assertNotIn((Keys.Escape, Keys.ControlM), key_sequences)

    def test_tab_applies_default_completion(self) -> None:
        session = InputSession.__new__(InputSession)
        completion = Mock()
        event = Mock()
        event.current_buffer.complete_state = SimpleNamespace(
            complete_index=None,
            completions=[completion],
        )

        session._apply_completion(event)

        event.current_buffer.apply_completion.assert_called_once_with(
            completion
        )

    def test_tab_applies_selected_completion(self) -> None:
        session = InputSession.__new__(InputSession)
        completions = [Mock(), Mock()]
        event = Mock()
        event.current_buffer.complete_state = SimpleNamespace(
            complete_index=1,
            completions=completions,
        )

        session._apply_completion(event)

        event.current_buffer.apply_completion.assert_called_once_with(
            completions[1]
        )

    def test_tab_starts_completion_when_no_options_are_loaded(self) -> None:
        session = InputSession.__new__(InputSession)
        event = Mock()
        event.current_buffer.complete_state = None

        session._apply_completion(event)

        event.current_buffer.start_completion.assert_called_once_with(
            select_first=True,
        )

    def test_submit_does_not_apply_default_path_completion(self) -> None:
        session = InputSession.__new__(InputSession)
        session._input_completer = Mock()
        session._input_completer.is_path_input.return_value = True
        session._select_default_completion = Mock()
        event = Mock()

        session._submit(event)

        session._select_default_completion.assert_not_called()
        event.current_buffer.validate_and_handle.assert_called_once_with()

    def test_submit_still_applies_default_command_completion(self) -> None:
        session = InputSession.__new__(InputSession)
        session._input_completer = Mock()
        session._input_completer.is_path_input.return_value = False
        session._select_default_completion = Mock()
        event = Mock()

        session._submit(event)

        session._select_default_completion.assert_called_once_with()
        event.current_buffer.validate_and_handle.assert_called_once_with()

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
