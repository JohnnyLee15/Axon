import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from axon.llm.retry import execute_with_retries_async


class AsyncRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_with_nonblocking_backoff(self) -> None:
        retryable_error = RuntimeError("try again")
        api_func = AsyncMock(side_effect=[retryable_error, "success"])
        is_retryable_error = Mock(return_value=True)
        ui = Mock()

        with patch("axon.llm.retry.asyncio.sleep", new=AsyncMock()) as sleep:
            result = await execute_with_retries_async(
                api_func=api_func,
                is_retryable_error=is_retryable_error,
                ui=ui,
            )

        self.assertEqual(result, "success")
        self.assertEqual(api_func.await_count, 2)
        sleep.assert_awaited_once_with(2)

    async def test_task_cancellation_propagates(self) -> None:
        request_started = asyncio.Event()

        async def api_func() -> None:
            request_started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(
            execute_with_retries_async(
                api_func=api_func,
                is_retryable_error=Mock(return_value=False),
                ui=Mock(),
            )
        )
        await request_started.wait()
        task.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await task


if __name__ == "__main__":
    unittest.main()
