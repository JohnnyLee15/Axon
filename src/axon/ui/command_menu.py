from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout.controls import (
    GetLinePrefixCallable,
    UIContent,
    UIControl,
)


MAX_VISIBLE_COMMANDS = 8


class CommandMenuControl(UIControl):
    def __init__(self) -> None:
        self._visible_completions = []
        self._start_index = 0
        self._selected_index = 0
        self._command_width = 0


    def preferred_height(
        self,
        _width: int,
        max_available_height: int,
        _wrap_lines: bool,
        _get_line_prefix: GetLinePrefixCallable | None,
    ) -> int:
        completion_state = get_app().current_buffer.complete_state
        if completion_state is None:
            return 0

        return min(
            len(completion_state.completions),
            MAX_VISIBLE_COMMANDS,
            max_available_height,
        )


    def _get_line(self, line_number: int) -> StyleAndTextTuples:
        completion_index = self._start_index + line_number
        completion = self._visible_completions[line_number]

        if completion_index == self._selected_index:
            command_style = "class:command-menu.item.current"
            description_style = "class:command-menu.description.current"
        else:
            command_style = "class:command-menu.item"
            description_style = "class:command-menu.description"

        command = completion.display_text.ljust(self._command_width)
        description = completion.display_meta_text
        return [
            (command_style, command),
            (description_style, f"  {description}"),
        ]


    def create_content(self, _width: int, _height: int) -> UIContent:
        completion_state = get_app().current_buffer.complete_state
        if completion_state is None or not completion_state.completions:
            self._visible_completions = []
            return UIContent()

        completions = completion_state.completions

        self._selected_index = (
            completion_state.complete_index
            if completion_state.complete_index is not None
            else 0
        )

        self._start_index = max(
            0,
            self._selected_index - MAX_VISIBLE_COMMANDS + 1,
        )

        self._visible_completions = completions[
            self._start_index:
            self._start_index + MAX_VISIBLE_COMMANDS
        ]

        self._command_width = max(
            len(completion.display_text)
            for completion in self._visible_completions
        )

        return UIContent(
            get_line=self._get_line,
            line_count=len(self._visible_completions),
            show_cursor=False,
        )
