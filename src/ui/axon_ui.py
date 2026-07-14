from typing import Any

from rich.console import Console
from rich.live import Live

from src.ui.select_menu import SelectMenu

from .prompt import Prompt
from .tool_renderers import ToolRenderers
from .views import Views
from .messages import Messages

OPTION_ID_KEY = "id"
OPTION_LABEL_KEY = "label"


class AxonUI:
    def __init__(self, console: Console):
        # TODO add a name to the database
        self._console = console
        self._prompt = Prompt(self._console)
        self._tool_renderers = ToolRenderers(self._console)
        self._views = Views(self._console)
        self._messages = Messages(self._console)
        self._select_menu = SelectMenu()
        self._views.display_welcome()


    def display_help(self, commands: dict) -> None:
        self._views.display_help(commands)


    def display_chat_names(self, chat_names: list[str]) -> None:
        self._views.display_chat_names(chat_names)


    def display_references(self, papers: list[tuple]) -> None:
        self._views.display_references(papers)


    def display_section(self, title: str) -> None:
        self._views.display_section(title)


    def select_option(self, options: list[dict[str, Any]]) -> str:
        labels = [option[OPTION_LABEL_KEY] for option in options]
        label_to_id = {
            option[OPTION_LABEL_KEY]: option[OPTION_ID_KEY]
            for option in options
        }
        selected_label = self._select_menu.select_item(labels)
        return label_to_id[selected_label]


    def listen(self, curr_tokens: int, context_size: int) -> str:
        return self._prompt.listen(curr_tokens, context_size)


    def wait(self) -> Live:
        return self._prompt.wait()


    def stream_response(self, response: str) -> None:
        self._prompt.stream_response(response)


    def display_tool_output(self, tool_name: str, results: dict[str, Any]) -> None:
        self._tool_renderers.display_tool_output(tool_name, results)


    def display_tool_args(self, tool_name: str, args: dict) -> None:
        self._tool_renderers.display_tool_args(tool_name, args)


    def info(self, text: str, leading_blank: bool = True) -> None:
        self._messages.info(text, leading_blank)


    def success(self, text: str, leading_blank: bool = True) -> None:
        self._messages.success(text, leading_blank)


    def warning(self, text: str, leading_blank: bool = True) -> None:
        self._messages.warning(text, leading_blank)


    def error(self, text: str, leading_blank: bool = True) -> None:
        self._messages.error(text, leading_blank)


    def unknown(self, text: str, leading_blank: bool = True) -> None:
        self._messages.unknown(text, leading_blank)


    def progress(self, text: str, leading_blank: bool = True) -> None:
        self._messages.progress(text, leading_blank)


    def confirm(self, text: str, leading_blank: bool = True) -> str:
        return self._messages.confirm(text, leading_blank)
