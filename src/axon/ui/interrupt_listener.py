from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.output import DummyOutput

from .settings import ESCAPE_KEY_TIMEOUT_SECONDS


class InterruptListener:
    def __init__(self) -> None:
        control = FormattedTextControl(
            text="",
            focusable=True,
        )

        self._key_bindings = KeyBindings()
        self._key_bindings.add("escape")(self._interrupt)

        self._application = Application[None](
            layout=Layout(
                container=Window(content=control),
                focused_element=control,
            ),
            key_bindings=self._key_bindings,
            output=DummyOutput(),
            full_screen=False,
        )
        self._application.ttimeoutlen = ESCAPE_KEY_TIMEOUT_SECONDS


    def _interrupt(self, event: KeyPressEvent) -> None:
        event.app.exit(result=None)


    async def wait(self) -> None:
        await self._application.run_async()
