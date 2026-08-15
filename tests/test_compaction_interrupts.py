import asyncio
import unittest
from contextlib import nullcontext
from unittest.mock import AsyncMock, Mock

from axon.llm.chat_llm import ChatLLM
from axon.session.chat_handlers import ChatHandlers


class ManualCompactionInterruptTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupted_manual_compaction_does_not_display_response(self) -> None:
        handlers = ChatHandlers.__new__(ChatHandlers)
        handlers._llm = Mock()
        handlers._llm.compact.return_value = object()
        handlers._ui = Mock()
        handlers._ui.wait.return_value = nullcontext()
        handlers._interrupt_coordinator = Mock()
        handlers._interrupt_coordinator.run = AsyncMock(
            return_value=(True, None)
        )

        await handlers.compact()

        handlers._ui.info.assert_called_once_with("Compaction interrupted.")
        handlers._ui.display_response.assert_not_called()
        handlers._ui.success.assert_not_called()


class AutoCompactionInterruptTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_waits_for_compaction_then_propagates(self) -> None:
        llm = ChatLLM.__new__(ChatLLM)
        compact_started = asyncio.Event()
        allow_compact_to_finish = asyncio.Event()

        async def compact() -> str:
            compact_started.set()
            await allow_compact_to_finish.wait()
            return "summary"

        llm.compact = compact
        completion_task = asyncio.create_task(llm._complete_compaction())
        await compact_started.wait()

        completion_task.cancel()
        await asyncio.sleep(0)

        self.assertFalse(completion_task.done())

        allow_compact_to_finish.set()
        with self.assertRaises(asyncio.CancelledError):
            await completion_task


if __name__ == "__main__":
    unittest.main()
