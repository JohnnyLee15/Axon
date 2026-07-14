from .theme import STYLES

def emphasis(text: object) -> str:
    return f"[{STYLES.EMPHASIS}]{text}[/{STYLES.EMPHASIS}]"


def strong(text: object) -> str:
    return f"[{STYLES.STRONG}]{text}[/{STYLES.STRONG}]"


def dim(text: object) -> str:
    return f"[{STYLES.DIM}]{text}[/{STYLES.DIM}]"


def panel_title(emoji: str, text: object) -> str:
    return strong(f"{emoji} {text}")