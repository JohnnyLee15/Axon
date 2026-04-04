from rich.console import Console, Group, NewLine
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown
from rich import box
from rich.spinner import Spinner
from config import *
import math
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import ANSI
import time
from select_menu import SelectMenu

class AxonUI:
    def __init__(self, console: Console):
        # TODO add a name to the database
        self._console = console
        self._select_menu = SelectMenu()
        self._kb = KeyBindings()
        self._bind_keys()
        self._display_welcome()


    def _display_welcome(self) -> None:
        logo = Text(LOGO, style=f"bold {MAIN_COLOUR_RICH}")
        table = Table(box=None, show_header=False, padding=0)
        panel = Panel(
            WELCOME_MESSAGE,
            border_style="bold",
            padding=(2,2),
            title="[bold]Welcome[/bold]",
            expand=False
        )

        table.add_column(justify="center")
        table.add_row(logo)
        table.add_row(panel)
        self._console.print(table)


    def _bind_keys(self) -> None:
        @self._kb.add("enter")
        def _(event):
            event.current_buffer.validate_and_handle()

        @self._kb.add("escape", "enter")
        def _(event):
            event.current_buffer.insert_text("\n")


    def listen(self, curr_tokens: int, context_size: int) -> str:
        percent_used = math.ceil((curr_tokens / context_size) * 100)
        p_colour = GREEN if percent_used < 65 else YELLOW if percent_used < 90 else RED

        p_text = f"[{p_colour}{percent_used}%{RESET}]"
        you_text = f"[{CYAN}{BOLD}You{RESET}] {CYAN}{BOLD}>{RESET}"

        return prompt(
            ANSI(f"\n{p_text} {you_text} "),
            multiline=True,
            key_bindings=self._kb,
            wrap_lines=True,
            prompt_continuation=lambda prompt_width, line_number, wrap_count: ""
        ).strip()


    def wait(self):
        renderable = Group(
            NewLine(),
            Spinner("dots", text=Text("Thinking...", style="bold"), style="bold")
        )
        return Live(
            renderable,
            console=self._console,
            transient=True,
            refresh_per_second=12
        )


    def stream_response(self, response: str) -> None:
        display_text = "<br>**[Axon] >** "

        with Live(
            console=self._console,
            refresh_per_second=30
        ) as live:
            for char in response:
                display_text += char
                live.update(Markdown(display_text))
                time.sleep(0.001)


    def select_item(self, items: list[str]) -> str:
        return self._select_menu.select_item(items)


    def display_help(self, commands: dict) -> None:
        table = Table(
            title="🧠 [bold]Axon Command Menu[/bold]",
            expand=False,
            header_style="bold",
            box=box.ROUNDED,
            padding=(0,2)
        )
        table.add_column("Command", style="bold cyan")
        table.add_column("Description")

        base_cmds = []
        grouped_cmds = {}

        for cmd in commands:
            item = commands[cmd]
            if "subcommands" in item:
                grouped_cmds[cmd] = item["subcommands"]
            else:
                base_cmds.append(item)

        for cmd in base_cmds:
            table.add_row(cmd["usage"], cmd["desc"])

        for cmd in grouped_cmds:
            sub_cmds = grouped_cmds[cmd]
            table.add_section()

            for sub_cmd in sub_cmds:
                props = sub_cmds[sub_cmd]
                table.add_row(props["usage"], props["desc"])

        self._console.print()
        self._console.print(table)


    def display_chat_names(self, chat_names: list[str]) -> None:
        if not chat_names:
            self._console.print("\n📭 [bold yellow]No saved chats found in the database.[/bold yellow]")
            return

        list_contents = ""
        for name in chat_names:
            list_contents += f"  [dim]•[/dim] [cyan]\"{name}\"[/cyan]\n"

        panel = Panel(
            list_contents.rstrip(),
            title ="📂 [bold]Saved Chats[/bold]",
            title_align="center",
            expand=False,
            border_style="bold"
        )

        self._console.print("\n")
        self._console.print(panel)