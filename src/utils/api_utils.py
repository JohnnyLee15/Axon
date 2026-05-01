from typing import Any, Callable
from rich.console import Console
import time

from src.utils.config import *

def execute_with_retries(
    api_func: Callable,
    console: Console,
    num_retries: int = 2,
    *args,
    **kwargs
) -> Any:
    for attempt in range(1, num_retries + 1):
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            if any(error_code in error_str for error_code in API_BUSY_ERROR_CODES):
                if attempt == num_retries:
                    console.print(f"\n❌ [bold red]Fatal: API unreachable after {attempt} attempts.[/bold red]")
                    raise e

                wait_time = 2 ** attempt
                console.print(f"\n⏳ [bold yellow]Failed {attempt} caused by Server congested. Retrying in {wait_time}s.[/bold yellow]")
                time.sleep(wait_time)
            else:
                raise e