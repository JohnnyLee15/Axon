from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown
from config import *
import math
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import ANSI
import time
from select_menu import SelectMenu

class AxonUI:
    def __init__(self):
        # TODO add a name to the database
        self._console = Console()
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
        @self._kb.add("escape", "enter")
        def _(event):
            event.current_buffer.validate_and_handle()


    def listen(self, curr_tokens: int) -> str:
        percent_used = math.ceil((curr_tokens / LLM_SMALL_CONTEXT_TOKS) * 100)
        p_colour = GREEN if percent_used < 65 else YELLOW if percent_used < 90 else RED

        p_text = f"[{p_colour}{percent_used}%{RESET}]"
        you_text = f"[{CYAN}{BOLD}You{RESET}] {CYAN}{BOLD}>{RESET}"
        submit_text = f"{DIM}(Esc + Enter to send){RESET}"

        return prompt(
            ANSI(f"\n{p_text} {you_text} {submit_text} "),
            multiline=True,
            key_bindings=self._kb,
            wrap_lines=True,
            prompt_continuation=lambda prompt_width, line_number, wrap_count: ""
        ).strip()


    def wait(self):
        self._console.print()
        return self._console.status(
            "[bold white]Thinking...[/bold white]",
            spinner="dots",
            spinner_style="bold white"
        )


    def stream_response(self, response: str) -> None:
        self._console.print(f"[bold white][Axon] > [/bold white]")
        display_text = ""

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
