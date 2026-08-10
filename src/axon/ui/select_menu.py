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
            prefix = f"{theme_colour(ansi=True)}>{ANSI_COLOURS.RESET} " if is_highlighted else "  "
            style = theme_colour(ansi=True) if is_highlighted else ""
            item_list_str += f"{prefix}{style}{item}{ANSI_COLOURS.RESET}\n"

        item_list_str +=  f"\n{ANSI_COLOURS.DIM}↑/↓ to move • Enter to select • Esc to cancel{ANSI_COLOURS.RESET}"
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
            self._items = []
            self._highlighted_idx = 0
            event.app.exit(result=selected_item)

        @self._kb.add("escape")
        def _(event):
            self._items = []
            self._highlighted_idx = 0
            event.app.exit(result=None)


    def select_item(
        self,
        items: list[str],
        selected_item: str | None = None,
    ) -> str | None:
        if not items:
            return None

        self._items = items

        if selected_item is not None and selected_item in items:
            self._highlighted_idx = items.index(selected_item)
        else:
            self._highlighted_idx = 0

        return self._app.run()