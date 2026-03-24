from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from config import *

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


    def listen(self) -> str:
        return self._console.input("\n[bold cyan]>[/bold cyan] ").strip()