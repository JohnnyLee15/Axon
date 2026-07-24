THEME_COLOUR = "cyan"
SYNTAX_THEME = "monokai"


class AnsiColours:
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"

    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"
    REVERSE = "\033[7m"


ANSI_COLOURS = AnsiColours()

ANSI_COLOURS_BY_NAME = {
    "cyan": ANSI_COLOURS.CYAN,
    "green": ANSI_COLOURS.GREEN,
    "yellow": ANSI_COLOURS.YELLOW,
    "red": ANSI_COLOURS.RED,
}


class MessageEmojis:
    INFO = "ℹ️"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    UNKNOWN = "❓"
    CONFIRM = "❓"
    PROGRESS = "⏳"

MESSAGE_EMOJIS = MessageEmojis()


class AxonToolEmojis:
    RUN = "⚡"
    TERMINAL = "💻"
    SEARCH = "🔍"
    MEMORY = "🧠"
    FILE = "📄"
    FILE_EDIT = "✨"
    FILE_CREATE = "📋"
    FILE_INSERT = "📥"

AXON_TOOL_EMOJIS = AxonToolEmojis()


class ViewEmojis:
    COMMAND_MENU = "🧠"
    EMPTY = "📭"
    SAVED_CHATS = "📂"
    REFERENCES = "📚"
    WELCOME = "👋"


VIEW_EMOJIS = ViewEmojis()


class Styles:
    EMPHASIS = f"bold {THEME_COLOUR}"
    STRONG = "bold"
    DIM = "dim"

STYLES = Styles()


def theme_colour(ansi: bool = False) -> str:
    if ansi:
        return ANSI_COLOURS_BY_NAME[THEME_COLOUR]

    return THEME_COLOUR