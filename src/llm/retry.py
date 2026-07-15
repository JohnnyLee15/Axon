from typing import Any, Callable
import time

from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis


DEFAULT_MAX_ATTEMPTS = 3


def execute_with_retries(
    api_func: Callable,
    is_retryable_error: Callable,
    ui: AxonUI,
    *args,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    **kwargs
) -> Any:
    for attempt in range(1, max_attempts + 1):
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            if not is_retryable_error(e):
                raise

            if attempt == max_attempts:
                ui.error(f"API unreachable after {emphasis(attempt)} attempts.")
                raise

            wait_time = 2 ** attempt
            ui.progress(
                f"API request failed on attempt {emphasis(attempt)}. "
                f"Retrying in {emphasis(wait_time)} seconds."
            )
            time.sleep(wait_time)
