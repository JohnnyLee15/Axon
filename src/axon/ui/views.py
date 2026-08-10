from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

from axon.commands.contracts import COMMAND_KEYS
from axon.db.models import ChatSummary
from axon.llm.contracts import LLM_CONTRACT

from .theme import STYLES, THEME_COLOUR, VIEW_EMOJIS
from .formatters import (
    strong,
    panel_title,
    emphasis,
    format_elapsed_time,
    format_timestamp,
)


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

[dim](Tip: Enter to send | Ctrl + J for newline)[/dim]"""

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


    def _partition_commands(
        self,
        commands: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        base_commands = []
        command_groups = []
        for command in commands.values():
            subcommands = command.get(COMMAND_KEYS.SUBCOMMANDS)

            if subcommands is None:
                base_commands.append(command)
            else:
                command_groups.append(subcommands)

        return base_commands, command_groups


    def _add_help_rows(self, table: Table, commands: list[dict]) -> None:
        for cmd in commands:
            table.add_row(cmd[COMMAND_KEYS.USAGE], cmd[COMMAND_KEYS.DESC])


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

        base_cmds, cmd_groups = self._partition_commands(commands)
        self._add_help_rows(table, base_cmds)

        for sub_cmds in cmd_groups:
            table.add_section()
            self._add_help_rows(table, list(sub_cmds.values()))

        self._console.print()
        self._console.print(table)


    def display_chats(self, chats: list[ChatSummary]) -> None:
        if not chats:
            self._console.print(f"\n{VIEW_EMOJIS.EMPTY} {strong('No saved chats found in the database.')}")
            return

        table = Table(
            title=panel_title(VIEW_EMOJIS.SAVED_CHATS, "Saved Chats"),
            box=box.ROUNDED,
            expand=False,
            padding=(0, 2),
        )
        table.add_column("Name", style=STYLES.EMPHASIS)
        table.add_column("Created")
        table.add_column("Last Accessed")

        for chat in chats:
            table.add_row(
                chat.name,
                format_timestamp(chat.created_at),
                format_timestamp(chat.last_accessed_at),
            )

        self._console.print()
        self._console.print(table)


    def _display_history_text(
        self,
        label: str,
        text: str,
        label_style: str,
    ) -> None:
        self._console.print()
        self._console.print(
            Text(f"[{label}] >", style=label_style),
            end=" ",
        )
        self._console.print(Markdown(text))


    def _display_history_tool_header(self, label: str, tool_name: Any) -> None:
        header = Text(f"[{label}] ", style=STYLES.DIM)
        header.append(
            str(tool_name),
            style=f"{STYLES.DIM} {THEME_COLOUR}",
        )
        self._console.print(header)


    def _display_history_tool_call(self, item: dict[str, Any]) -> None:
        tool_name = item.get(LLM_CONTRACT.NAME, "Unknown tool")
        tool_args = item.get(LLM_CONTRACT.ARGS, {})

        self._console.print()
        self._display_history_tool_header("Tool", tool_name)

        for arg_name, arg_value in tool_args.items():
            argument = Text(
                f"{arg_name}: {arg_value}",
                style=STYLES.DIM,
            )
            self._console.print(Padding(argument, (0, 0, 0, 2)))


    def _display_history_tool_response(self, item: dict[str, Any]) -> None:
        tool_name = item.get(LLM_CONTRACT.NAME, "Unknown tool")
        result = item.get(LLM_CONTRACT.RESULT, "")

        self._console.print()
        self._display_history_tool_header("Result", tool_name)
        self._console.print(
            Padding(
                Text(str(result), style=STYLES.DIM),
                (0, 0, 0, 2),
            )
        )


    def display_history(self, history: list[dict[str, Any]]) -> None:
        self.display_section("Chat History")

        for item in history:
            item_type = item.get(LLM_CONTRACT.TYPE)

            if item_type == LLM_CONTRACT.USER_TEXT:
                self._display_history_text(
                    label="You",
                    text=str(item.get(LLM_CONTRACT.TEXT, "")),
                    label_style=STYLES.EMPHASIS,
                )
            elif item_type == LLM_CONTRACT.MODEL_TEXT:
                self._display_history_text(
                    label="Axon",
                    text=str(item.get(LLM_CONTRACT.TEXT, "")),
                    label_style=STYLES.STRONG,
                )
            elif item_type == LLM_CONTRACT.TOOL_CALL:
                self._display_history_tool_call(item)
            elif item_type == LLM_CONTRACT.TOOL_RESPONSE:
                self._display_history_tool_response(item)


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


    def display_work_duration(self, total_seconds: int) -> None:
        elapsed_text = format_elapsed_time(total_seconds)
        self._console.print()
        self._console.print(
            Text(f"Worked for {elapsed_text}", style=STYLES.DIM)
        )
