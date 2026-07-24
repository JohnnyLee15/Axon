from pathlib import Path
import difflib

from src.utils.file_system import get_path_relative_to_project_root, resolve_filepath

from .tool_contracts import TOOL_RESULTS, TOOL_NAMES, TOOL_ARGS


FIRST_LINE_NUMBER = 1
BEFORE_FIRST_LINE = 0
DIFF_CONTEXT_LINES = 3
MAX_READ_CHARS = 50_000
READ_TRUNCATION_NOTICE = (
    f"\n\n[Output truncated at {MAX_READ_CHARS:,} characters. "
    f"Request a narrower line range or use "
    f"{TOOL_NAMES.EXECUTE_SHELL_CMD} to search the file.]"
)


def create_file(path: str, content: str) -> dict:
    try:
        filepath = resolve_filepath(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("x", encoding="utf-8") as file:
            file.write(content)
    except FileExistsError:
        return {
            TOOL_RESULTS.CONTENT: (
                f"File already exists: \"{filepath}\". "
                f"Use {TOOL_NAMES.REPLACE_IN_FILE} to modify it."
            )
        }
    except Exception as e:
        return {TOOL_RESULTS.CONTENT: f"File creation failed: {e}."}

    return {TOOL_RESULTS.CONTENT: f"File created successfully: \"{filepath}\"."}



def _create_diff(filepath: Path, old_content: str, new_content: str) -> str:
    display_path = get_path_relative_to_project_root(filepath)

    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{display_path}",
        tofile=f"b/{display_path}",
        n=DIFF_CONTEXT_LINES,
    )

    return "".join(diff)


def _get_replacement_error(
    filepath: Path,
    file_content: str,
    old_str: str,
    new_str: str
) -> str | None:
    if not old_str:
        return f"Could not edit \"{filepath}\": {TOOL_ARGS.OLD_STR} cannot be empty."

    if old_str == new_str:
        return (
            f"Could not edit \"{filepath}\": "
            f"{TOOL_ARGS.OLD_STR} and {TOOL_ARGS.NEW_STR} are identical."
        )

    match_count = file_content.count(old_str)

    if match_count == 0:
        return (
            f"Could not edit \"{filepath}\": {TOOL_ARGS.OLD_STR} was not found exactly. "
            "Inspect the current file and try again with matching whitespace "
            "and indentation."
        )

    if match_count > 1:
        return (
            f"Could not edit \"{filepath}\": {TOOL_ARGS.OLD_STR} appears "
            f"{match_count} times. Provide a larger, unique {TOOL_ARGS.OLD_STR}."
        )

    return None


def replace_in_file(path: str, old_str: str, new_str: str) -> dict:
    try:
        filepath = resolve_filepath(path)
        file_content = filepath.read_text(encoding="utf-8")
        replacement_error = _get_replacement_error(
            filepath,
            file_content,
            old_str,
            new_str,
        )
        if replacement_error is not None:
            return {TOOL_RESULTS.CONTENT: replacement_error}

        new_content = file_content.replace(old_str, new_str, 1)
        filepath.write_text(new_content, encoding="utf-8")
        diff_text = _create_diff(filepath, file_content, new_content)
    except FileNotFoundError:
        return {TOOL_RESULTS.CONTENT: f"File does not exist: \"{filepath}\"."}
    except IsADirectoryError:
        return {TOOL_RESULTS.CONTENT: f"Path is a directory, not a file: \"{filepath}\"."}
    except Exception as e:
        return {TOOL_RESULTS.CONTENT: f"File replacement failed: {e}."}

    return {
        TOOL_RESULTS.CONTENT: (
            f"File edited successfully: \"{filepath}\".\n\n"
            f"```diff\n{diff_text}```"
        ),
        TOOL_RESULTS.DIFF: diff_text,
    }


def _get_line_range_error(
    filepath: Path,
    start_line: int,
    end_line: int,
    total_lines: int,
) -> str | None:
    if start_line < FIRST_LINE_NUMBER or end_line < FIRST_LINE_NUMBER:
        return (
            f"{TOOL_ARGS.START_LINE} and {TOOL_ARGS.END_LINE} must be "
            f"{FIRST_LINE_NUMBER}-indexed line numbers."
        )

    if start_line > total_lines:
        return (
            f"Cannot read from line {start_line} in \"{filepath}\": "
            f"the file only has {total_lines} lines."
        )

    if start_line > end_line:
        return (
            f"{TOOL_ARGS.START_LINE}={start_line} is greater than "
            f"{TOOL_ARGS.END_LINE}={end_line}."
        )

    return None


def _format_numbered_lines(
    lines: list[str],
    start_line: int,
    end_line: int
) -> tuple[str, int, bool]:
    selected_lines = lines[(start_line - FIRST_LINE_NUMBER):end_line]
    line_number_width = len(str(end_line))

    formatted_content = "\n".join(
        f"{line_number:{line_number_width}} | {line}"
        for line_number, line in enumerate(selected_lines, start=start_line)
    )

    if len(formatted_content) <= MAX_READ_CHARS:
        return formatted_content, end_line, False

    content_limit = MAX_READ_CHARS - len(READ_TRUNCATION_NOTICE)
    truncated_content = formatted_content[:content_limit].rstrip("\n")
    actual_end_line = start_line + truncated_content.count("\n")

    return truncated_content + READ_TRUNCATION_NOTICE, actual_end_line, True


def read_file(
    path: str,
    start_line: int | None = None,
    end_line: int | None = None
) -> dict:
    try:
        filepath = resolve_filepath(path)
        file_content = filepath.read_text(encoding="utf-8")
        lines = file_content.splitlines()
        total_lines = len(lines)

        if total_lines == 0:
            return {
                TOOL_RESULTS.CONTENT: f"File is empty: \"{filepath}\".",
                TOOL_RESULTS.START_LINE: FIRST_LINE_NUMBER,
                TOOL_RESULTS.END_LINE: 0,
            }

        resolved_start_line = start_line if start_line is not None else FIRST_LINE_NUMBER
        resolved_end_line = end_line if end_line is not None else total_lines

        line_range_error = _get_line_range_error(
            filepath,
            resolved_start_line,
            resolved_end_line,
            total_lines,
        )
        if line_range_error is not None:
            return {TOOL_RESULTS.CONTENT: line_range_error}

        resolved_end_line = min(resolved_end_line, total_lines)
        formatted_content, actual_line_end, truncated = _format_numbered_lines(
            lines,
            resolved_start_line,
            resolved_end_line,
        )
    except FileNotFoundError:
        return {TOOL_RESULTS.CONTENT: f"File does not exist: \"{filepath}\"."}
    except IsADirectoryError:
        return {TOOL_RESULTS.CONTENT: f"Path is a directory, not a file: \"{filepath}\"."}
    except Exception as e:
        return {TOOL_RESULTS.CONTENT: f"File read failed: {e}."}

    return {
        TOOL_RESULTS.CONTENT: formatted_content,
        TOOL_RESULTS.START_LINE: resolved_start_line,
        TOOL_RESULTS.END_LINE: actual_line_end,
        TOOL_RESULTS.TRUNCATED: truncated,
    }


def _get_insertion_error(
    filepath: Path,
    insert_text: str,
    insert_after_line: int,
    total_lines: int,
) -> str | None:
    if not insert_text:
        return (
            f"Could not insert into \"{filepath}\": "
            f"{TOOL_ARGS.INSERT_TEXT} cannot be empty."
        )

    if insert_after_line < BEFORE_FIRST_LINE:
        return (
            f"{TOOL_ARGS.INSERT_AFTER_LINE} must be a non-negative integer. "
            f"Use {BEFORE_FIRST_LINE} to insert at the beginning of the file."
        )

    if insert_after_line > total_lines:
        return (
            f"Cannot insert after line {insert_after_line} in \"{filepath}\": "
            f"the file only has {total_lines} lines."
        )

    return None


def _build_inserted_content(
    lines: list[str],
    insert_text: str,
    insert_after_line: int,
) -> str:
    if not insert_text.endswith("\n"):
        insert_text += "\n"

    appending_to_file = insert_after_line == len(lines)
    if appending_to_file and lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    lines.insert(insert_after_line, insert_text)
    return "".join(lines)


def insert_to_file(
    path: str,
    insert_text: str,
    insert_after_line: int | None = None
) -> dict:
    try:
        filepath = resolve_filepath(path)
        file_content = filepath.read_text(encoding="utf-8")
        lines = file_content.splitlines(keepends=True)
        total_lines = len(lines)

        resolved_insert_after_line = (
            insert_after_line
            if insert_after_line is not None
            else total_lines
        )
        insertion_error = _get_insertion_error(
            filepath,
            insert_text,
            resolved_insert_after_line,
            total_lines
        )
        if insertion_error is not None:
            return {TOOL_RESULTS.CONTENT: insertion_error}

        new_content = _build_inserted_content(lines, insert_text, resolved_insert_after_line)
        filepath.write_text(new_content, encoding="utf-8")
        diff_text = _create_diff(filepath, file_content, new_content)
    except FileNotFoundError:
        return {TOOL_RESULTS.CONTENT: f"File does not exist: \"{filepath}\"."}
    except IsADirectoryError:
        return {TOOL_RESULTS.CONTENT: f"Path is a directory, not a file: \"{filepath}\"."}
    except Exception as e:
        return {TOOL_RESULTS.CONTENT: f"File insertion failed: {e}."}

    return {
        TOOL_RESULTS.CONTENT: (
            f"Text inserted successfully into \"{filepath}\".\n\n"
            f"```diff\n{diff_text}```"
        ),
        TOOL_RESULTS.DIFF: diff_text,
    }

