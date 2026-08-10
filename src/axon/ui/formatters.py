from datetime import datetime

from .theme import STYLES

def emphasis(text: object) -> str:
    return f"[{STYLES.EMPHASIS}]{text}[/{STYLES.EMPHASIS}]"


def strong(text: object) -> str:
    return f"[{STYLES.STRONG}]{text}[/{STYLES.STRONG}]"


def dim(text: object) -> str:
    return f"[{STYLES.DIM}]{text}[/{STYLES.DIM}]"


def panel_title(emoji: str, text: object) -> str:
    return strong(f"{emoji} {text}")


def format_elapsed_time(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"

    if minutes:
        return f"{minutes}m {seconds:02d}s"

    return f"{seconds}s"


def format_timestamp(timestamp: str) -> str:
    try:
        local_time = datetime.fromisoformat(timestamp).astimezone()
    except ValueError:
        return timestamp

    date_text = local_time.strftime("%b %d, %Y")
    time_text = local_time.strftime("%I:%M %p").lstrip("0")
    return f"{date_text} {time_text}"
