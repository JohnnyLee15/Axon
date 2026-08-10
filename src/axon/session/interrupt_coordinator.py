import asyncio
from collections.abc import Coroutine
from typing import Any

from axon.ui.axon_ui import AxonUI


class InterruptCoordinator:
    def __init__(self, ui: AxonUI) -> None:
        self._ui = ui


    async def run(
        self,
        operation: Coroutine[Any, Any, Any],
    ) -> tuple[bool, Any | None]:
        operation_task = asyncio.create_task(operation)
        interrupt_task = asyncio.create_task(self._ui.wait_for_interrupt())

        try:
            done, _ = await asyncio.wait(
                {operation_task, interrupt_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if operation_task in done:
                value = await operation_task
                return False, value

            return True, None

        finally:
            for task in (operation_task, interrupt_task):
                if not task.done():
                    task.cancel()

            await asyncio.gather(
                operation_task,
                interrupt_task,
                return_exceptions=True,
            )