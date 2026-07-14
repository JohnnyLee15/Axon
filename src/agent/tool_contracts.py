class ToolNames:
    SEARCH_FOR_CHUNKS = "search_for_chunks"
    REPLACE_IN_FILE = "replace_in_file"
    EXECUTE_BASH_CMD = "execute_bash_cmd"
    CREATE_FILE = "create_file"
    READ_FILE = "read_file"
    INSERT_TO_FILE = "insert_to_file"

TOOL_NAMES = ToolNames()


class ToolArgs:
    PATH = "path"
    CONTENT = "content"
    DIFF = "diff"
    OLD_STR = "old_str"
    NEW_STR = "new_str"
    CMD = "cmd"
    QUERY = "query"
    START_LINE = "start_line"
    END_LINE = "end_line"
    INSERT_TEXT = "insert_text"
    INSERT_AFTER_LINE = "insert_after_line"

TOOL_ARGS = ToolArgs()


class ToolResults:
    CONTENT = "content"
    DIFF = "diff"
    START_LINE = "start_line"
    END_LINE = "end_line"
    CHUNK_COUNT = "chunk_count"
    DOC_COUNT = "doc_count"

TOOL_RESULTS = ToolResults()