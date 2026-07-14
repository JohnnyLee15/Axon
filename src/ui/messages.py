from rich.console import Console

from .theme import MESSAGE_EMOJIS


class Messages:
    def __init__(self, console: Console) -> None:
        self._console = console

    def _print(self, emoji: str, text: str, leading_blank: bool = True) -> None:
        if leading_blank:
            self._console.print()

        self._console.print(f"{emoji} {text}")

    def info(self, text: str, leading_blank: bool = True) -> None:
        self._print(MESSAGE_EMOJIS.INFO, text, leading_blank)

    def success(self, text: str, leading_blank: bool = True) -> None:
        self._print(MESSAGE_EMOJIS.SUCCESS, text, leading_blank)

    def warning(self, text: str, leading_blank: bool = True) -> None:
        self._print(MESSAGE_EMOJIS.WARNING, text, leading_blank)

    def error(self, text: str, leading_blank: bool = True) -> None:
        self._print(MESSAGE_EMOJIS.ERROR, text, leading_blank)

    def unknown(self, text: str, leading_blank: bool = True) -> None:
        self._print(MESSAGE_EMOJIS.UNKNOWN, text, leading_blank)

    def progress(self, text: str, leading_blank: bool = True) -> None:
        self._print(MESSAGE_EMOJIS.PROGRESS, text, leading_blank)

    def confirm(self, text: str, leading_blank: bool = True) -> str:
        if leading_blank:
            self._console.print()

        return self._console.input(f"{MESSAGE_EMOJIS.CONFIRM} {text}")



