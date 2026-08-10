from enum import Enum


class CommandKeys:
    SUBCOMMANDS = "subcommands"
    USAGE = "usage"
    DESC = "desc"
    ARGC = "argc"
    HANDLER = "handler"
COMMAND_KEYS = CommandKeys()


class CommandHandlerNames:
    SAVE_CHAT = "save_chat"
    LOAD_CHAT = "load_chat"
    CLEAR_CHAT = "clear_chat"
    DISPLAY_HISTORY = "display_history"
    SET_LIMIT = "set_limit"
    COMPACT = "compact"
    AUTO_COMPACT = "auto_compact"
    LIST_CHATS = "list_chats"
    DELETE_CHAT = "delete_chat"
    CHAT_ROLL = "chat_roll"

    LOAD_PDFS = "load_pdfs"
    CLEAR_LIBRARY = "clear_library"

    CLEAR_SCREEN = "clear_screen"
    SELECT_MODEL = "select_model"
    EXIT = "exit"
    HELP = "help"
    TOGGLE_AGENT = "toggle_agent"
COMMAND_HANDLER_NAMES = CommandHandlerNames()


class CommandResult(Enum):
    EXIT = "exit"
