from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

from src.commands.contracts import COMMAND_KEYS

from .theme import STYLES, VIEW_EMOJIS
from .formatters import strong, panel_title, dim, emphasis


LOGO = """
⠀⠀⠀⣤⣤⣤⣤⣤⣤⣤⠀⠀⠀⢠⣤⣤⣤⣤⡀⠀⠀⣠⣤⣤⣤⣤⠀⠀⠀⢀⣀⣤⣤⣤⣄⣀⠀⠀⠀⠀⢠⣤⣤⣤⣄⠀⠀⢠⣤⣤⣤⣤
⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠘⣿⣿⣿⣿⣧⠀⢰⣿⣿⣿⣿⡏⠀⢀⣴⣿⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⢸⣿⣿⣿⣿⣆⠀⢸⣿⣿⣿⣿
⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠸⣿⣿⣿⣿⣆⣿⣿⣿⣿⡟⠀⠀⣾⣿⣿⣿⣿⡿⣿⣿⣿⣿⣿⡆⠀⢸⣿⣿⣿⣿⣿⡄⢸⣿⣿⣿⣿
⠀⢠⣿⣿⣿⣿⠹⣿⣿⣿⣿⡄⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⢸⣿⣿⣿⣿⡏⠀⢸⣿⣿⣿⣿⣿⠀⢸⣿⣿⣿⣿⣿⣷⣸⣿⣿⣿⣿
⠀⢸⣿⣿⣿⣿⠀⣿⣿⣿⣿⣇⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣧⡀⠀⠀⢸⣿⣿⣿⣿⡇⠀⠀⣿⣿⣿⣿⣿⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⣿⣿⣿⣿⣿⣤⣿⣿⣿⣿⣿⠀⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⢸⣿⣿⣿⣿⣇⠀⢰⣿⣿⣿⣿⣿⠀⢸⣿⣿⣿⣿⢹⣿⣿⣿⣿⣿⣿
⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⣼⣿⣿⣿⣿⠇⣿⣿⣿⣿⣿⡀⠘⣿⣿⣿⣿⣿⣶⣾⣿⣿⣿⣿⡏⠀⢸⣿⣿⣿⣿⠀⢻⣿⣿⣿⣿⣿
⣸⣿⣿⣿⣿⠋⠉⠙⣿⣿⣿⣿⣧⢠⣿⣿⣿⣿⡿⠀⢸⣿⣿⣿⣿⣇⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⢸⣿⣿⣿⣿⠀⠈⣿⣿⣿⣿⣿
⠛⠻⠿⠿⠛⠀⠀⠀⠛⠿⠿⠿⠛⠸⠿⠿⠿⠿⠃⠀⠀⠻⠿⠿⠿⠿⠀⠀⠀⠙⠛⠻⠿⠿⠛⠋⠁⠀⠀⠀⠘⠛⠿⠿⠛⠀⠀⠘⠛⠿⠿⠟
"""

WELCOME_MESSAGE = f"""Good to see you — let's skip the reading and get straight to the facts.
Type {emphasis('/help')} at any time to see available commands.

[dim](Tip: Enter to send | Esc + Enter for newline)[/dim]"""

UNKNOWN_TITLE_STR = "Unknown Title"


class Views:
    def __init__(self, console: Console) -> None:
        self._console = console


    def display_welcome(self) -> None:
        logo = Text(LOGO, style=STYLES.EMPHASIS)
        table = Table(box=None, show_header=False, padding=0)
        panel = Panel(
            WELCOME_MESSAGE,
            border_style=STYLES.STRONG,
            padding=(2,2),
            title=strong("Welcome"),
            expand=False
        )

        table.add_column(justify="center")
        table.add_row(logo)
        table.add_row(panel)
        self._console.print(table)


    def display_help(self, commands: dict) -> None:
        table = Table(
            title=panel_title(VIEW_EMOJIS.COMMAND_MENU, "Axon Command Menu"),
            expand=False,
            header_style=STYLES.STRONG,
            box=box.ROUNDED,
            padding=(0,2)
        )
        table.add_column("Command", style=STYLES.EMPHASIS)
        table.add_column("Description")

        base_cmds = []
        grouped_cmds = {}

        for cmd in commands:
            item = commands[cmd]
            if COMMAND_KEYS.SUBCOMMANDS in item:
                grouped_cmds[cmd] = item[COMMAND_KEYS.SUBCOMMANDS]
            else:
                base_cmds.append(item)

        for cmd in base_cmds:
            table.add_row(cmd[COMMAND_KEYS.USAGE], cmd[COMMAND_KEYS.DESC])

        for cmd in grouped_cmds:
            sub_cmds = grouped_cmds[cmd]
            table.add_section()

            for sub_cmd in sub_cmds:
                props = sub_cmds[sub_cmd]
                table.add_row(props[COMMAND_KEYS.USAGE], props[COMMAND_KEYS.DESC])

        self._console.print()
        self._console.print(table)


    def display_chat_names(self, chat_names: list[str]) -> None:
        if not chat_names:
            self._console.print(f"\n{VIEW_EMOJIS.EMPTY} {strong('No saved chats found in the database.')}")
            return

        list_contents = ""
        for name in chat_names:
            list_contents += f"  {dim('•')} \"{emphasis(name)}\"\n"

        panel = Panel(
            list_contents.rstrip(),
            title=panel_title(VIEW_EMOJIS.SAVED_CHATS, "Saved Chats"),
            title_align="center",
            expand=False,
            border_style=STYLES.STRONG
        )

        self._console.print("\n")
        self._console.print(panel)


    def display_references(self, papers: list[tuple]) -> None:
        self._console.print()
        self._console.rule(style=STYLES.STRONG)
        self._console.print(f"{VIEW_EMOJIS.REFERENCES} {strong('References')}")

        for i, (title, doi, arxiv, pmcid, pmid) in enumerate(papers, start=1):
            title = title if title else UNKNOWN_TITLE_STR

            identifiers = {
                "DOI": doi,
                "arXiv": arxiv,
                "PMCID": pmcid,
                "PMID": pmid
            }

            id_str = " • ".join(
                f"{paper_id}: {identifiers[paper_id]}" for paper_id in identifiers
                if identifiers[paper_id] is not None
            )
            self._console.print(f"\n  {emphasis(i)} {strong(title)}")

            # TODO: Make tab constant
            if id_str:
                self._console.print(f"    • {id_str}", highlight=False)


    def display_section(self, title: str) -> None:
        self._console.print()
        self._console.rule(emphasis(title), style=STYLES.STRONG)
