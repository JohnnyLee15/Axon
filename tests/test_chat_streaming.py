import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from axon.llm.chat_llm import ChatLLM
from axon.llm.contracts import LLM_CONTRACT


class ChatStreamingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.adapter = Mock()
        self.adapter.count_tokens = AsyncMock(return_value=10)
        self.ui = Mock()
        self.llm = ChatLLM(
            ui=self.ui,
            llm_adapter=self.adapter,
            chat_model="gemini-test",
            context_size=1_000,
        )

    async def test_streams_chunks_and_records_completed_turn(self) -> None:
        async def response_stream():
            yield "Hello "
            yield "world"

        self.adapter.generate_text_stream.return_value = response_stream()

        chunks = [
            chunk
            async for chunk in self.llm.query_chat(
                user_input="Hello",
                chunks=None,
            )
        ]

        self.assertEqual(chunks, ["Hello ", "world"])
        history = self.llm.get_history()
        self.assertEqual(history[0][LLM_CONTRACT.TEXT], "Hello")
        self.assertEqual(history[1][LLM_CONTRACT.TEXT], "Hello world")

    async def test_completed_empty_stream_records_both_turns(self) -> None:
        async def response_stream():
            if False:
                yield ""

        self.adapter.generate_text_stream.return_value = response_stream()

        chunks = [
            chunk
            async for chunk in self.llm.query_chat(
                user_input="Are you there?",
                chunks=None,
            )
        ]

        self.assertEqual(chunks, [])
        history = self.llm.get_history()
        self.assertEqual(history[0][LLM_CONTRACT.TEXT], "Are you there?")
        self.assertEqual(history[1][LLM_CONTRACT.TEXT], "")

    async def test_generation_error_records_only_user_turn(self) -> None:
        async def response_stream():
            raise RuntimeError("stream failed")
            yield ""

        self.adapter.generate_text_stream.return_value = response_stream()

        chunks = [
            chunk
            async for chunk in self.llm.query_chat(
                user_input="Keep this",
                chunks=None,
            )
        ]

        self.assertEqual(chunks, [])
        history = self.llm.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][LLM_CONTRACT.TEXT], "Keep this")
        self.ui.error.assert_called_once()

    async def test_cancellation_does_not_record_partial_turn(self) -> None:
        chunk_received = asyncio.Event()

        async def response_stream():
            yield "partial"
            await asyncio.Event().wait()

        async def consume_response() -> None:
            async for _ in self.llm.query_chat(
                user_input="Interrupt this",
                chunks=None,
            ):
                chunk_received.set()

        self.adapter.generate_text_stream.return_value = response_stream()
        task = asyncio.create_task(consume_response())
        await chunk_received.wait()
        task.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await task

        history = self.llm.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][LLM_CONTRACT.TEXT], "Interrupt this")


if __name__ == "__main__":
    unittest.main()
