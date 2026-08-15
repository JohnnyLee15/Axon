from .tool_contracts import TOOL_ARGS, TOOL_NAMES

SEARCH_LIBRARY_SCHEMA = {
    "name": TOOL_NAMES.SEARCH_LIBRARY,
    "description": (
        "Search Axon's scientific paper database for relevant excerpts when you need more information to answer the user."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.QUERY: {
                "type": "string",
                "description": "A standalone search query."
            }
        },
        "required": [TOOL_ARGS.QUERY]
    }
}

EXECUTE_SHELL_CMD_SCHEMA = {
    "name": TOOL_NAMES.EXECUTE_SHELL_CMD,
    "description": (
        "Execute a shell command exactly as it should be typed in a terminal. "
        "Do not add backslashes before ordinary single or double quotes unless the shell command itself requires them."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.CMD: {
                "type": "string",
                "description": "The exact shell command to execute as a raw, unescaped shell string."
            }
        },
        "required": [TOOL_ARGS.CMD]
    }
}

CREATE_FILE_SCHEMA = {
    "name": TOOL_NAMES.CREATE_FILE,
    "description": (
        "Create a new file at the given path with the provided contents. "
        "Use this only for new files; use replace_in_file to modify existing files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.PATH: {
                "type": "string",
                "description": "The path where the new file should be created."
            },
            TOOL_ARGS.CONTENT: {
                "type": "string",
                "description": (
                    "The exact full contents to write into the new file. "
                    "Do not wrap the contents in markdown fences."
                )
            }
        },
        "required": [TOOL_ARGS.PATH, TOOL_ARGS.CONTENT]
    }
}

REPLACE_IN_FILE_SCHEMA = {
    "name": TOOL_NAMES.REPLACE_IN_FILE,
    "description": (
        "Edit an existing file by replacing one exact text section with new text. "
        "Use this only for modifying existing files; use create_file for new files. "
        "When editing code, prefer replacing a complete syntactic block, such as "
        "an entire function, loop, or if/else block, rather than a tiny prefix that may leave overlapping code behind."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.PATH: {
                "type": "string",
                "description": "The path of the file to edit."
            },
            TOOL_ARGS.OLD_STR: {
                "type": "string",
                "description": (
                    "The exact text currently in the file to replace. "
                    "It must match exactly, including whitespace and indentation, and appear only once."
                )
            },
            TOOL_ARGS.NEW_STR: {
                "type": "string",
                "description": (
                    "The exact replacement text. "
                    "Do not wrap the contents in markdown fences."
                )
            }
        },
        "required": [TOOL_ARGS.PATH, TOOL_ARGS.OLD_STR, TOOL_ARGS.NEW_STR]
    }
}

READ_FILE_SCHEMA = {
    "name": TOOL_NAMES.READ_FILE,
    "description": (
        "Read the contents of a file. Returns the text with line numbers to help you navigate. "
        "You can optionally provide start_line and end_line to read a specific section of a file."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.PATH: {
                "type": "string",
                "description": "The path of the file to read."
            },
            TOOL_ARGS.START_LINE: {
                "type": "integer",
                "description": "Optional 1-indexed first line to read, inclusive. Defaults to 1."
            },
            TOOL_ARGS.END_LINE: {
                "type": "integer",
                "description": "Optional 1-indexed last line to read, inclusive. Defaults to the end of the file."
            }
        },
        "required": [TOOL_ARGS.PATH]
    }
}

INSERT_TO_FILE_SCHEMA = {
    "name": TOOL_NAMES.INSERT_TO_FILE,
    "description": (
        "Insert text into an existing file after a specific line number. "
        "Use read_file first if you need to see line numbers. "
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.PATH: {
                "type": "string",
                "description": "The path of the file to edit."
            },
            TOOL_ARGS.INSERT_TEXT: {
                "type": "string",
                "description": (
                    "The exact text to insert. "
                    "Do not wrap the contents in markdown fences."
                )
            },
            TOOL_ARGS.INSERT_AFTER_LINE: {
                "type": "integer",
                "description": (
                    "Optional 1-indexed line number to insert after. "
                    "Use 0 to insert at the beginning. Defaults to the end of the file."
                )
            }
        },
        "required": [TOOL_ARGS.PATH, TOOL_ARGS.INSERT_TEXT]
    }
}

SEARCH_WEB_SCHEMA = {
    "name": TOOL_NAMES.SEARCH_WEB,
    "description": (
        "Searches the public web for the supplied query and returns a concise, "
        "source-grounded summary with source titles and URLs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            TOOL_ARGS.QUERY: {
                "type": "string",
                "description": "A concise, standalone web search query.",
            }
        },
        "required": [TOOL_ARGS.QUERY],
    },
}

TOOL_SCHEMAS = [
    SEARCH_LIBRARY_SCHEMA,
    SEARCH_WEB_SCHEMA,
    EXECUTE_SHELL_CMD_SCHEMA,
    CREATE_FILE_SCHEMA,
    REPLACE_IN_FILE_SCHEMA,
    READ_FILE_SCHEMA,
    INSERT_TO_FILE_SCHEMA,
]
