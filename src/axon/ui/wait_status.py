import time

from rich.text import Text

from .theme import STYLES
from .formatters import format_elapsed_time


class WaitStatus:
    def __init__(
        self,
        show_cancel_hint: bool,
        started_at: float | None = None,
    ) -> None:
        self._show_cancel_hint = show_cancel_hint
        self._started_at = (
            started_at if started_at is not None else time.monotonic()
        )


    def __rich__(self) -> Text:
        elapsed_seconds = int(time.monotonic() - self._started_at)
        elapsed_text = format_elapsed_time(elapsed_seconds)

        text = Text("Working", style=STYLES.DIM)

        if self._show_cancel_hint:
            text.append(
                f" ({elapsed_text}  •  Esc to interrupt)",
                style=STYLES.DIM,
            )
        else:
            text.append(f" ({elapsed_text})", style=STYLES.DIM)

        return text
