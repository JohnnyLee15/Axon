from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown
from config import *
import time
import math

class AxonUI:
    def __init__(self):
        # TODO add a name to the database
        self._console = Console()
        self._init()


    def _init(self) -> None:
        logo = Text(LOGO, style=f"bold {COLOUR}")
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


    def listen(self, curr_tokens: int) -> str:
        percent_used = math.ceil((curr_tokens / LLM_CHAT_MAX_TOKS) * 100)
        p_colour = "green" if percent_used < 65 else "yellow" if percent_used < 90 else "red"
        p_text = f"[[{p_colour}]{percent_used}%][/{p_colour}]"
        cursor = f"\n{p_text} [bold {COLOUR}][You] >[/bold {COLOUR}] "
        return self._console.input(cursor).strip()


    def wait(self):
        return self._console.status(
            "[bold white]Thinking...[/bold white]",
            spinner="dots",
            spinner_style="bold white"
        )


    def stream_response(self, response: str) -> None:
        self._console.print(f"\n[bold white][Axon] > [/bold white]")
        display_text = ""

        with Live(
            console=self._console,
            refresh_per_second=30
        ) as live:
            for char in response:
                display_text += char
                live.update(Markdown(display_text))
                time.sleep(0.001)
