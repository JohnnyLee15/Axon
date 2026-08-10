from typing import Any

from rich.console import Console
from rich.live import Live

from axon.db.models import ChatSummary
from axon.ui.select_menu import SelectMenu

from .prompt import Prompt
from .tool_renderers import ToolRenderers
from .views import Views
from .messages import Messages
from .contracts import OPTION_DESC_KEY, OPTION_KEY
from .interrupt_listener import InterruptListener
from .formatters import format_timestamp


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
        self._interrupt_listener = InterruptListener()
        self._views.display_welcome()


    def display_help(self, commands: dict) -> None:
        self._views.display_help(commands)


    def display_chats(self, chats: list[ChatSummary]) -> None:
        self._views.display_chats(chats)


    async def select_chat(self, chats: list[ChatSummary]) -> str | None:
        if not chats:
            return None

        rows = [
            (
                chat.name,
                format_timestamp(chat.created_at),
                format_timestamp(chat.last_accessed_at),
            )
            for chat in chats
        ]
        name_width = max(len("Name"), *(len(row[0]) for row in rows))
        created_width = max(len("Created"), *(len(row[1]) for row in rows))

        header = (
            f"{'Name':<{name_width}}  "
            f"{'Created':<{created_width}}  "
            "Last Accessed"
        )
        labels_to_names = {
            (
                f"{name:<{name_width}}  "
                f"{created:<{created_width}}  "
                f"{last_accessed}"
            ): name
            for name, created, last_accessed in rows
        }

        selected_label = await self._select_menu.select_item(
            list(labels_to_names),
            header=header,
        )
        return labels_to_names.get(selected_label)


    def display_history(self, history: list[dict[str, Any]]) -> None:
        self._views.display_history(history)


    def display_references(self, papers: list[tuple]) -> None:
        self._views.display_references(papers)


    def display_section(self, title: str) -> None:
        self._views.display_section(title)


    def clear_screen(self) -> None:
        self._console.clear()
        self._suppress_next_prompt_newline = True


    async def select_item(
        self,
        options: list[dict[str, Any]],
        selected_option: Any | None = None,
    ) -> Any | None:
        option_values = [option[OPTION_KEY] for option in options]
        item_texts = [
            f"{value:,}" if isinstance(value, int) else str(value)
            for value in option_values
        ]
        descriptions = [
            str(option[OPTION_DESC_KEY])
            for option in options
        ]
        items_to_options = dict(zip(item_texts, option_values, strict=True))
        options_to_items = dict(zip(option_values, item_texts, strict=True))

        selected_item = await self._select_menu.select_item(
            item_texts,
            descriptions=descriptions,
            selected_item=options_to_items.get(selected_option),
        )

        return items_to_options.get(selected_item)


    async def listen(
            self, curr_tokens: int | None,
            context_size: int,
            model_name: str,
        ) -> str:
        if self._suppress_next_prompt_newline:
            self._suppress_next_prompt_newline = False
        else:
            self._console.print()

        return await self._prompt.listen(
            curr_tokens=curr_tokens,
            context_size=context_size,
            model_name=model_name,
        )


    def wait(
        self,
        show_cancel_hint: bool = False,
        started_at: float | None = None,
    ) -> Live:
        return self._prompt.wait(
            show_cancel_hint=show_cancel_hint,
            started_at=started_at,
        )


    def stream_response(self, response: str) -> None:
        self._prompt.stream_response(response)


    def display_tool_output(self, tool_name: str, results: dict[str, Any]) -> None:
        self._tool_renderers.display_tool_output(tool_name, results)


    def display_tool_args(self, tool_name: str, args: dict) -> None:
        self._tool_renderers.display_tool_args(tool_name, args)


    def display_goodbye(self) -> None:
        self.info("Shutting down Axon. Goodbye!")


    def display_interrupted(self) -> None:
        self.info("Response interrupted.")


    def display_work_duration(self, total_seconds: int) -> None:
        self._views.display_work_duration(total_seconds)


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


    async def wait_for_interrupt(self) -> None:
        await self._interrupt_listener.wait()
