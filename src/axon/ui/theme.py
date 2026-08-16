import os

from blessed import Terminal
from prompt_toolkit.styles import Style


USER_DARK_INPUT_BACKGROUND = "#333333"
USER_LIGHT_INPUT_BACKGROUND = "#f0f0f0"
USER_DEFAULT_INPUT_BACKGROUND = "default"
LIGHT_ANSI_BACKGROUND_COLOURS = {7, 15}
DARK_ANSI_BACKGROUND_COLOURS = {0, 8}
BACKGROUND_LUMINANCE_THRESHOLD = 128
TERMINAL_BACKGROUND_QUERY_TIMEOUT = 0.15
UNKNOWN_TERMINAL_BACKGROUND = (-1, -1, -1)
THEME_COLOUR = "cyan"
PROMPT_THEME_COLOUR = f"ansi{THEME_COLOUR}"
SYNTAX_THEME = "monokai"


def _is_light_ansi_background(colour_hint: str | None) -> bool | None:
    if not colour_hint:
        return None

    try:
        background_colour = int(colour_hint.rsplit(";", maxsplit=1)[-1])
    except ValueError:
        return None

    if background_colour in LIGHT_ANSI_BACKGROUND_COLOURS:
        return True

    if background_colour in DARK_ANSI_BACKGROUND_COLOURS:
        return False

    return None


def _is_light_rgb_background(
    background_colour: tuple[int, int, int],
) -> bool | None:
    if background_colour == UNKNOWN_TERMINAL_BACKGROUND:
        return None

    red, green, blue = background_colour
    luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
    return luminance >= BACKGROUND_LUMINANCE_THRESHOLD


def _is_light_terminal_background() -> bool | None:
    try:
        background_colour = Terminal().get_bgcolor(
            timeout=TERMINAL_BACKGROUND_QUERY_TIMEOUT,
            bits=8,
        )
    except Exception:
        return None

    return _is_light_rgb_background(background_colour)


def get_user_input_background() -> str:
    is_light_background = _is_light_ansi_background(
        os.environ.get("COLORFGBG")
    )

    if is_light_background is None:
        is_light_background = _is_light_terminal_background()

    if is_light_background is True:
        return USER_LIGHT_INPUT_BACKGROUND

    if is_light_background is False:
        return USER_DARK_INPUT_BACKGROUND

    return USER_DEFAULT_INPUT_BACKGROUND


USER_INPUT_BACKGROUND = get_user_input_background()


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
    CREDENTIAL = "🔑"
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


PROMPT_STYLE = Style.from_dict({
    "command-menu": "bg:default",

    "command-menu.item": "fg:default bg:default",
    "command-menu.item.current": f"fg:{PROMPT_THEME_COLOUR} bg:default",

    "command-menu.description": "fg:default bg:default dim",
    "command-menu.description.current": f"fg:{PROMPT_THEME_COLOUR} bg:default nodim",

    "user-input": f"fg:default bg:{USER_INPUT_BACKGROUND}",

    "input-status": "fg:default bg:default dim",
    "resize-notice": "fg:default bg:default dim",
})


def theme_colour(ansi: bool = False) -> str:
    if ansi:
        return ANSI_COLOURS_BY_NAME[THEME_COLOUR]

    return THEME_COLOUR
