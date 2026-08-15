from collections.abc import AsyncIterator
from pathlib import Path

from rich.console import Console, Group, NewLine
from rich.text import Text
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner

import math

from pylatexenc.latex2text import LatexNodes2Text

from axon.config.paths import PROMPT_HISTORY_PATH

from .theme import ANSI_COLOURS, theme_colour, STYLES
from .input_session import InputSession
from .wait_status import DEFAULT_WAIT_LABEL, WaitStatus


CONTEXT_NOT_FULL_PERCENT = 65
CONTEXT_NEAR_FULL_PERCENT = 90
UNKNOWN_CONTEXT_USAGE_DISPLAY = "?"
REFRESH_RATE = 12


class Prompt:
    def __init__(self, console: Console, command_options: dict[str, str]) -> None:
        self._console = console

        self._latex_converter = LatexNodes2Text()

        self._input_session = InputSession(
            command_options=command_options,
            history_path=PROMPT_HISTORY_PATH,
        )


    def _get_percentage_colour(self, percent_used: int) -> str:
        if percent_used < CONTEXT_NOT_FULL_PERCENT:
            return ANSI_COLOURS.GREEN

        if percent_used < CONTEXT_NEAR_FULL_PERCENT:
            return ANSI_COLOURS.YELLOW

        return ANSI_COLOURS.RED


    def _get_percentage_text(self, curr_tokens: int | None, context_size: int) -> str:
        if curr_tokens is None:
            return (
                f"[{ANSI_COLOURS.DIM}"
                f"{UNKNOWN_CONTEXT_USAGE_DISPLAY}"
                f"{ANSI_COLOURS.RESET}]"
            )

        percent_used = math.ceil((curr_tokens / context_size) * 100)
        p_colour = self._get_percentage_colour(percent_used)
        return (
            f"[{p_colour}{percent_used}%"
            f"{ANSI_COLOURS.RESET}]"
        )


    def _get_display_cwd(self) -> Path:
        cwd = Path.cwd()
        home = Path.home()
        try:
            display_cwd = Path("~") / cwd.relative_to(home)
        except ValueError:
            display_cwd = cwd

        return display_cwd


    async def listen(
        self,
        curr_tokens: int | None,
        context_size: int,
        model_name: str,
    ) -> str:
        p_text = self._get_percentage_text(curr_tokens, context_size)
        you_text = (
            f"[{theme_colour(ansi=True)}{ANSI_COLOURS.BOLD}You{ANSI_COLOURS.RESET}] "
            f"{theme_colour(ansi=True)}{ANSI_COLOURS.BOLD}>{ANSI_COLOURS.RESET}"
        )

        status_text = f"  {model_name}  •  {self._get_display_cwd()}"
        prompt_text = f"{p_text} {you_text} "

        return (
            await self._input_session.prompt(
                prompt_text=prompt_text,
                status_text=status_text,
            )
        ).strip()


    def _create_wait_renderable(
        self,
        show_cancel_hint: bool,
        started_at: float | None,
        label: str,
    ) -> Group:
        status = WaitStatus(
            show_cancel_hint=show_cancel_hint,
            started_at=started_at,
            label=label,
        )

        return Group(
            NewLine(),
            Spinner("dots", text=status, style=STYLES.DIM),
        )


    def wait(
        self,
        show_cancel_hint: bool = False,
        started_at: float | None = None,
        label: str = DEFAULT_WAIT_LABEL,
    ) -> Live:
        renderable = self._create_wait_renderable(
            show_cancel_hint=show_cancel_hint,
            started_at=started_at,
            label=label,
        )

        return Live(
            renderable,
            console=self._console,
            transient=True,
            refresh_per_second=REFRESH_RATE,
        )


    async def stream_response(
        self,
        response_stream: AsyncIterator[str],
        started_at: float,
    ) -> str:
        response = ""
        initial_renderable = self._create_wait_renderable(
            show_cancel_hint=True,
            started_at=started_at,
            label=DEFAULT_WAIT_LABEL,
        )

        with Live(
            initial_renderable,
            console=self._console,
            refresh_per_second=REFRESH_RATE,
        ) as live:
            try:
                async for response_chunk in response_stream:
                    response += response_chunk
                    display_response = self._latex_converter.latex_to_text(response)
                    live.update(
                        Markdown(f"<br>**[Axon] >** {display_response}"),
                        refresh=True,
                    )
            finally:
                if not response:
                    live.update(Text(""), refresh=True)

        return response


    def display_response(self, response: str) -> None:
        response = self._latex_converter.latex_to_text(response)
        self._console.print(
            Markdown(f"<br>**[Axon] >** {response}")
        )


    def clear_screen(self) -> None:
        self._input_session.clear_screen()
