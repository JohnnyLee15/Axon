import unittest
from unittest.mock import AsyncMock, Mock

from axon.ui.interrupt_listener import InterruptListener


class InterruptListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_runs_application_asynchronously(self) -> None:
        listener = InterruptListener.__new__(InterruptListener)
        listener._application = Mock()
        listener._application.run_async = AsyncMock()

        await listener.wait()

        listener._application.run_async.assert_awaited_once_with()

    async def test_interrupt_exits_application(self) -> None:
        listener = InterruptListener.__new__(InterruptListener)
        event = Mock()

        listener._interrupt(event)

        event.app.exit.assert_called_once_with(result=None)


if __name__ == "__main__":
    unittest.main()
