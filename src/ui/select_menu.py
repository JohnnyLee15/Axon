from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import ANSI

from .theme import ANSI_COLOURS, theme_colour

class SelectMenu:
    def __init__(self):
        self._highlighted_idx = 0
        self._items = []

        self._control = FormattedTextControl(self._get_list)
        self._window = Window(content=self._control)

        self._kb = KeyBindings()
        self._bind_keys()

        self._app = Application(
            layout=Layout(self._window),
            key_bindings=self._kb,
            full_screen=False,
            erase_when_done=True
        )


    def _get_list(self) -> ANSI:
        item_list_str = ""

        for i, item in enumerate(self._items):
            is_highlighted = (i == self._highlighted_idx)
            prefix = f"{theme_colour(ansi=True)}{ANSI_COLOURS.BOLD}>{ANSI_COLOURS.RESET} " if is_highlighted else "  "
            style = ANSI_COLOURS.REVERSE if is_highlighted else ""
            item_list_str += f"{prefix}{style}{ANSI_COLOURS.BOLD}{item}{ANSI_COLOURS.RESET}\n"

        item_list_str +=  "\n↑/↓ to move and Enter to select."
        return ANSI(item_list_str)


    def _bind_keys(self) -> None:
        @self._kb.add("up")
        def _(event):
            self._highlighted_idx = (self._highlighted_idx - 1) % len(self._items)
            event.app.invalidate()

        @self._kb.add("down")
        def _(event):
            self._highlighted_idx = (self._highlighted_idx + 1) % len(self._items)
            event.app.invalidate()

        @self._kb.add("enter")
        def _(event):
            selected_item = self._items[self._highlighted_idx]
            self._highlighted_idx = 0
            self._items = []
            event.app.exit(result=selected_item)


    def select_item(self, items: list[str]) -> str | None:
        if not items:
            return None

        self._items = items
        return self._app.run()