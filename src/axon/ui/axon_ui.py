from typing import Any

from rich.console import Console
from rich.live import Live

from axon.ui.select_menu import SelectMenu

from .prompt import Prompt
from .tool_renderers import ToolRenderers
from .views import Views
from .messages import Messages
from .contracts import OPTION_ID_KEY, OPTION_LABEL_KEY


class AxonUI:
    def __init__(self, command_options: dict[str, str]):
        # TODO add a name to the database
        self._suppress_next_prompt_newline = False
        self._console = Console(highlight=False)
        self._prompt = Prompt(console=self._console, command_options=command_options)
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


    def clear_screen(self) -> None:
        self._console.clear()
        self._suppress_next_prompt_newline = True


    def select_item(
        self,
        options: list[dict[str, Any]],
        selected_id: Any | None = None,
    ) -> Any | None:
        labels = [option[OPTION_LABEL_KEY] for option in options]

        id_to_label = {
            option[OPTION_ID_KEY]: option[OPTION_LABEL_KEY]
            for option in options
        }

        label_to_id = {
            option[OPTION_LABEL_KEY]: option[OPTION_ID_KEY]
            for option in options
        }

        selected_label = self._select_menu.select_item(
            labels,
            selected_item=id_to_label.get(selected_id),
        )

        return label_to_id.get(selected_label)


    def listen(
            self, curr_tokens: int | None,
            context_size: int,
            model_name: str,
        ) -> str:
        if self._suppress_next_prompt_newline:
            self._suppress_next_prompt_newline = False
        else:
            self._console.print()

        return self._prompt.listen(
            curr_tokens=curr_tokens,
            context_size=context_size,
            model_name=model_name,
        )


    def wait(self) -> Live:
        return self._prompt.wait()


    def stream_response(self, response: str) -> None:
        self._prompt.stream_response(response)


    def display_tool_output(self, tool_name: str, results: dict[str, Any]) -> None:
        self._tool_renderers.display_tool_output(tool_name, results)


    def display_tool_args(self, tool_name: str, args: dict) -> None:
        self._tool_renderers.display_tool_args(tool_name, args)


    def display_goodbye(self) -> None:
        self.info("Shutting down Axon. Goodbye!")


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


    def request_secret(self, text: str, leading_blank: bool = True) -> str:
        return self._messages.request_secret(text, leading_blank)
