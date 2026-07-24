from typing import Any
import os

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

from src.utils.file_system import get_path_relative_to_project_root, get_file_ext
from src.agent.tool_contracts import TOOL_ARGS, TOOL_NAMES, TOOL_RESULTS

from .theme import AXON_TOOL_EMOJIS, MESSAGE_EMOJIS, SYNTAX_THEME
from .formatters import panel_title, emphasis


SYNTAX_DIFF = "diff"
SYNTAX_SHELL = "batch" if os.name == "nt" else "shell"
UNKNOWN_PATH_STR = "Unknown Path"
EOF_STR = "EOF"


class ToolRenderers:
    def __init__(self, console: Console) -> None:
        self._console = console
        self._init_renderers()


    def _init_renderers(self) -> None:
        self._tool_renderers = {
            TOOL_NAMES.SEARCH_LIBRARY: self._render_result_rag_search,
            TOOL_NAMES.REPLACE_IN_FILE: self._render_result_replace_in_file,
            TOOL_NAMES.EXECUTE_SHELL_CMD: self._render_result_shell,
            TOOL_NAMES.CREATE_FILE: self._render_result_create_file,
            TOOL_NAMES.READ_FILE: self._render_result_read_file,
            TOOL_NAMES.INSERT_TO_FILE: self._render_result_insert_to_file
        }

        self._arg_renderers = {
            TOOL_NAMES.SEARCH_LIBRARY: self._render_args_rag,
            TOOL_NAMES.REPLACE_IN_FILE: self._render_args_replace_in_file,
            TOOL_NAMES.EXECUTE_SHELL_CMD: self._render_args_shell,
            TOOL_NAMES.CREATE_FILE: self._render_args_create_file,
            TOOL_NAMES.READ_FILE: self._render_args_read_file,
            TOOL_NAMES.INSERT_TO_FILE: self._render_args_insert_to_file
        }


    def _get_display_str_and_ext(self, filepath: str) -> tuple[str, str]:
        display_path = get_path_relative_to_project_root(filepath)
        display_str = str(display_path) if display_path else filepath
        ext = get_file_ext(display_str)
        return display_str, ext


    def _render_result_replace_in_file(self, results: dict[str, Any]) -> None:
        output = results[TOOL_RESULTS.CONTENT]
        diff = results.get(TOOL_RESULTS.DIFF, None)

        if diff:
            syntax = Syntax(diff, SYNTAX_DIFF, theme=SYNTAX_THEME, word_wrap=True)
            self._console.print(Panel(syntax, title=panel_title(AXON_TOOL_EMOJIS.FILE_EDIT, "File Edits")))
        else:
            self._console.print(Panel(output, title=panel_title(MESSAGE_EMOJIS.WARNING, "Edit Status")))


    def _render_result_shell(self, results: dict[str, Any]) -> None:
        output = results[TOOL_RESULTS.CONTENT]
        syntax = Syntax(output, SYNTAX_SHELL, theme=SYNTAX_THEME, word_wrap=True)
        self._console.print(Panel(syntax, title=panel_title(AXON_TOOL_EMOJIS.TERMINAL, "Terminal Output")))


    def _render_result_create_file(self, results: dict[str, Any]) -> None:
        output = results[TOOL_RESULTS.CONTENT]
        self._console.print(Panel(output, title=panel_title(AXON_TOOL_EMOJIS.FILE_CREATE, "File Status")))


    def _render_result_rag_search(self,  results: dict[str, Any]) -> None:
        result_text = results[TOOL_RESULTS.CONTENT]
        if not result_text:
            self._console.print(
                Panel(
                    "No relevant chunks found in the database.",
                    title=panel_title(AXON_TOOL_EMOJIS.FILE, "RAG Search Results")
                )
            )
            return

        chunk_count = results.get(TOOL_RESULTS.CHUNK_COUNT, 0)
        doc_count = results.get(TOOL_RESULTS.DOC_COUNT, 0)

        summary = (
            f"{AXON_TOOL_EMOJIS.SEARCH} Successfully extracted {emphasis(chunk_count)} semantic chunks "
            f"across {emphasis(doc_count)} relevant document(s)."
        )
        self._console.print(Panel(summary, title=panel_title(AXON_TOOL_EMOJIS.FILE, "RAG Search Results")))


    def _render_result_read_file(self, results: dict[str, Any]) -> None:
        start_line = results.get(TOOL_RESULTS.START_LINE, None)
        end_line = results.get(TOOL_RESULTS.END_LINE, None)
        truncated = results.get(TOOL_RESULTS.TRUNCATED, False)

        if start_line is None or end_line is None:
            self._console.print(
                Panel(
                    results[TOOL_RESULTS.CONTENT],
                    title=panel_title(MESSAGE_EMOJIS.WARNING, "Error Reading File"),
                )
            )
            return

        success_title = panel_title(AXON_TOOL_EMOJIS.FILE, "File Read")

        if end_line == 0:
            self._console.print(Panel(results[TOOL_RESULTS.CONTENT], title=success_title))
            return

        message = (
            f"{MESSAGE_EMOJIS.SUCCESS} Successfully read lines "
            f"{emphasis(start_line)} to {emphasis(end_line)} into memory."
        )
        if truncated:
            message += " Output was truncated."

        self._console.print(Panel(message, title=success_title))


    def _render_result_insert_to_file(self, results: dict[str, Any]) -> None:
        output = results[TOOL_RESULTS.CONTENT]
        diff = results.get(TOOL_RESULTS.DIFF, None)

        if diff:
            syntax = Syntax(diff, SYNTAX_DIFF, theme=SYNTAX_THEME, word_wrap=True)
            self._console.print(Panel(syntax, title=panel_title(AXON_TOOL_EMOJIS.FILE_EDIT, "File Edits")))
        else:
            self._console.print(Panel(output, title=panel_title(MESSAGE_EMOJIS.WARNING, "Edit Status")))


    def display_tool_output(self, tool_name: str, results: dict[str, Any]) -> None:
        renderer = self._tool_renderers[tool_name]
        self._console.print()
        renderer(results)


    def _render_args_shell(self, args: dict) -> None:
        cmd = args.get(TOOL_ARGS.CMD, "")
        syntax = Syntax(cmd, SYNTAX_SHELL, theme=SYNTAX_THEME, word_wrap=True)
        self._console.print(Panel(syntax, title=panel_title(AXON_TOOL_EMOJIS.RUN, "Axon is Running")))


    def _render_args_replace_in_file(self, args: dict) -> None:
        old_str = args.get(TOOL_ARGS.OLD_STR, "")
        new_str = args.get(TOOL_ARGS.NEW_STR, "")
        display_str, ext = self._get_display_str_and_ext(args.get(TOOL_ARGS.PATH, UNKNOWN_PATH_STR))
        search_syntax = Syntax(old_str, ext, theme=SYNTAX_THEME, word_wrap=True)
        replace_syntax = Syntax(new_str, ext, theme=SYNTAX_THEME, word_wrap=True)

        group = Group(
            Text(f"{AXON_TOOL_EMOJIS.SEARCH} Replacing this exact block:"),
            search_syntax,
            Text(f"\n {AXON_TOOL_EMOJIS.RUN} With this new block:"),
            replace_syntax
        )

        self._console.print(Panel(group, title=panel_title(AXON_TOOL_EMOJIS.RUN, f"Intended Edit: {emphasis(display_str)}")))


    def _render_args_create_file(self, args: dict) -> None:
        content = args.get(TOOL_ARGS.CONTENT, "")
        display_str, ext = self._get_display_str_and_ext(args.get(TOOL_ARGS.PATH, UNKNOWN_PATH_STR))

        syntax = Syntax(content, ext, theme=SYNTAX_THEME, line_numbers=True, word_wrap=True)
        self._console.print(Panel(syntax, title=panel_title(AXON_TOOL_EMOJIS.FILE_CREATE, f"Creating File: {emphasis(display_str)}")))


    def _render_args_rag(self, args: dict) -> None:
        query = args.get(TOOL_ARGS.QUERY, "")
        self._console.print(f"{AXON_TOOL_EMOJIS.MEMORY} Axon is searching memory for: \"{emphasis(query)}\"")


    def _render_args_read_file(self, args: dict) -> None:
        start_line = args.get(TOOL_ARGS.START_LINE, 1)
        end_line = args.get(TOOL_ARGS.END_LINE, EOF_STR)
        display_str, _ = self._get_display_str_and_ext(args.get(TOOL_ARGS.PATH, UNKNOWN_PATH_STR))

        self._console.print(Panel(
            f"Scanning lines {emphasis(start_line)} to {emphasis(end_line)}",
            title=panel_title(AXON_TOOL_EMOJIS.FILE, f"Inspecting File: {emphasis(display_str)}"),
        ))


    def _render_args_insert_to_file(self, args: dict) -> None:
        insert_text = args.get(TOOL_ARGS.INSERT_TEXT, "")
        insert_after_line = args.get(TOOL_ARGS.INSERT_AFTER_LINE, None)
        display_str, ext = self._get_display_str_and_ext(args.get(TOOL_ARGS.PATH, UNKNOWN_PATH_STR))

        syntax = Syntax(insert_text, ext, theme=SYNTAX_THEME, line_numbers=False, word_wrap=True)
        self._console.print(Panel(
            syntax,
            title=panel_title(
                AXON_TOOL_EMOJIS.FILE_INSERT,
                f"Inserting into: {emphasis(display_str)} after line {emphasis(insert_after_line)}",
            ),
        ))


    def display_tool_args(self, tool_name: str, args: dict) -> None:
        renderer = self._arg_renderers[tool_name]
        self._console.print()
        renderer(args)
