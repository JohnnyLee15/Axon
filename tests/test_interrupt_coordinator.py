import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from axon.session.interrupt_coordinator import InterruptCoordinator


class InterruptCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_completed_when_operation_finishes_first(self) -> None:
        ui = Mock()
        never_interrupt = asyncio.Event()
        ui.wait_for_interrupt = AsyncMock(side_effect=never_interrupt.wait)
        coordinator = InterruptCoordinator(ui)

        async def operation() -> str:
            return "completed value"

        interrupted, value = await coordinator.run(operation())

        self.assertFalse(interrupted)
        self.assertEqual(value, "completed value")

    async def test_interrupt_cancels_operation_and_waits_for_cleanup(self) -> None:
        ui = Mock()
        operation_started = asyncio.Event()
        operation_cleaned_up = asyncio.Event()

        async def wait_for_interrupt() -> None:
            await operation_started.wait()

        async def operation() -> None:
            try:
                operation_started.set()
                await asyncio.Event().wait()
            finally:
                operation_cleaned_up.set()

        ui.wait_for_interrupt = AsyncMock(side_effect=wait_for_interrupt)
        coordinator = InterruptCoordinator(ui)

        interrupted, value = await coordinator.run(operation())

        self.assertTrue(interrupted)
        self.assertIsNone(value)
        self.assertTrue(operation_cleaned_up.is_set())

    async def test_operation_completion_wins_when_both_tasks_finish(self) -> None:
        ui = Mock()
        ui.wait_for_interrupt = AsyncMock(return_value=None)
        coordinator = InterruptCoordinator(ui)

        async def operation() -> None:
            return

        interrupted, value = await coordinator.run(operation())

        self.assertFalse(interrupted)
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()
