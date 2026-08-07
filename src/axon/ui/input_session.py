from pathlib import Path

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.application import Application
from prompt_toolkit.filters import has_completions, is_done
from prompt_toolkit.layout import (
    BufferControl,
    ConditionalContainer,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.containers import VerticalAlign
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.layout.controls import FormattedTextControl

from .command_menu import CommandMenuControl, MAX_VISIBLE_COMMANDS
from .theme import PROMPT_STYLE


USER_INPUT_VERTICAL_PADDING = 1


class InputSession:
    def __init__(self, command_options: dict[str, str], history_path: Path) -> None:
        self._prompt_text = ANSI("")
        self._status_text = ""

        self._buffer = Buffer(
            completer=WordCompleter(
                list(command_options),
                sentence=True,
                meta_dict=command_options,
            ),
            complete_while_typing=True,
            history=FileHistory(str(history_path)),
            multiline=True,
            accept_handler=self._accept_input,
        )

        self._key_bindings = KeyBindings()
        self._bind_keys()

        self._application = Application[str](
            layout=self._create_layout(),
            key_bindings=self._key_bindings,
            style=PROMPT_STYLE,
            full_screen=False,
        )


    def _get_user_input_height(self) -> int:
        input_lines = self._buffer.document.line_count
        padding_lines = USER_INPUT_VERTICAL_PADDING * 2
        return input_lines + padding_lines


    def _get_status_text(self) -> str:
        return self._status_text


    def _accept_input(self, buffer: Buffer) -> bool:
        get_app().exit(result=buffer.text)
        return True


    def _move_completion(self, offset: int) -> None:
        completion_state = self._buffer.complete_state
        if completion_state is None or not completion_state.completions:
            return

        current_index = (
            completion_state.complete_index
            if completion_state.complete_index is not None
            else 0
        )
        next_index = (
            current_index + offset
        ) % len(completion_state.completions)

        self._buffer.go_to_completion(next_index)


    def _select_default_completion(self) -> None:
        completion_state = self._buffer.complete_state
        if completion_state is None or not completion_state.completions:
            return

        if completion_state.complete_index is None:
            self._buffer.go_to_completion(0)


    def _submit(self, event: KeyPressEvent) -> None:
        self._select_default_completion()
        event.current_buffer.validate_and_handle()


    def _insert_newline(self, event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")


    def _select_previous_completion(self, _event: KeyPressEvent) -> None:
        self._move_completion(-1)


    def _select_next_completion(self, _event: KeyPressEvent) -> None:
        self._move_completion(1)


    def _interrupt(self, event: KeyPressEvent) -> None:
        event.app.exit(exception=KeyboardInterrupt())


    def _handle_eof(self, event: KeyPressEvent) -> None:
        if event.current_buffer.text:
            event.current_buffer.delete()
            return

        event.app.exit(exception=EOFError())


    def _bind_keys(self) -> None:
        self._key_bindings.add("enter")(self._submit)
        self._key_bindings.add("escape", "enter")(self._insert_newline)

        self._key_bindings.add(
            "up",
            filter=has_completions,
        )(self._select_previous_completion)

        self._key_bindings.add(
            "down",
            filter=has_completions,
        )(self._select_next_completion)

        self._key_bindings.add("c-c")(self._interrupt)
        self._key_bindings.add("c-d")(self._handle_eof)


    def _get_prompt_text(self) -> ANSI:
        return self._prompt_text


    def _create_input_control(self) -> BufferControl:
        return BufferControl(
            buffer=self._buffer,
            input_processors=[
                BeforeInput(self._get_prompt_text),
            ],
        )


    def _create_input_padding(self) -> Window:
        return Window(
            height=USER_INPUT_VERTICAL_PADDING,
            char=" ",
            style="class:user-input",
        )


    def _create_user_input_container(
        self,
        input_control: BufferControl,
    ) -> HSplit:
        input_window = Window(
            content=input_control,
            wrap_lines=True,
            dont_extend_height=True,
            style="class:user-input",
        )

        return HSplit(
            [
                self._create_input_padding(),
                input_window,
                self._create_input_padding(),
            ],
            align=VerticalAlign.TOP,
            height=self._get_user_input_height,
            style="class:user-input",
        )


    def _create_command_menu(self) -> ConditionalContainer:
        return ConditionalContainer(
            content=Window(
                content=CommandMenuControl(),
                height=Dimension(max=MAX_VISIBLE_COMMANDS),
                dont_extend_height=True,
                style="class:command-menu",
            ),
            filter=has_completions & ~is_done,
        )


    def _create_status_line(self) -> ConditionalContainer:
        return ConditionalContainer(
            content=Window(
                content=FormattedTextControl(self._get_status_text),
                height=1,
                dont_extend_height=True,
                style="class:input-status",
            ),
            filter=~has_completions & ~is_done,
        )


    def _create_layout(self) -> Layout:
        input_control = self._create_input_control()

        root_container = HSplit(
            [
                self._create_user_input_container(input_control),
                self._create_status_line(),
                self._create_command_menu(),
            ],
            align=VerticalAlign.TOP,
        )

        return Layout(
            container=root_container,
            focused_element=input_control,
        )




    def prompt(self, prompt_text: str, status_text: str) -> str:
        self._prompt_text = ANSI(prompt_text)
        self._status_text = status_text
        self._buffer.reset()

        return self._application.run()
