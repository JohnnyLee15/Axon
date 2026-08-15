import unittest
from contextlib import nullcontext
from unittest.mock import ANY, AsyncMock, Mock

from axon.agent.tool_contracts import TOOL_RESULTS
from axon.session.agent_runner import AgentRunner
from axon.session.query_runner import QueryRunner


class QueryRunnerInterruptTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._llm = Mock()
        self._llm.rewrite_query = Mock(return_value=object())
        self._ui = Mock()
        self._ui.wait.return_value = nullcontext()
        self._library_search_tool = Mock()
        self._reference_presenter = Mock()
        self._coordinator = Mock()
        self._coordinator.run = AsyncMock()
        self._runner = QueryRunner(
            llm=self._llm,
            ui=self._ui,
            library_search_tool=self._library_search_tool,
            reference_presenter=self._reference_presenter,
            interrupt_coordinator=self._coordinator,
        )

    async def test_rewrite_interruption_preserves_user_message(self) -> None:
        self._coordinator.run.return_value = (True, None)

        await self._runner.process_query("Keep this message")

        self._llm.add_user_history.assert_called_once_with("Keep this message")
        self._ui.display_interrupted.assert_called_once_with()
        self._library_search_tool.search_library.assert_not_called()

    async def test_response_interruption_preserves_user_message(self) -> None:
        self._coordinator.run.side_effect = [
            (False, "rewritten query"),
            (True, None),
        ]
        self._library_search_tool.search_library.return_value = {
            TOOL_RESULTS.CONTENT: "chunks",
            TOOL_RESULTS.RAW_CHUNKS: {},
        }
        self._llm.query_chat = Mock(return_value=object())

        await self._runner.process_query("Keep this message")

        self._llm.add_user_history.assert_not_called()
        self._ui.display_interrupted.assert_called_once_with()
        self._ui.stream_response.assert_called_once_with(
            response_stream=self._llm.query_chat.return_value,
            started_at=ANY,
        )


class AgentRunnerInterruptTests(unittest.IsolatedAsyncioTestCase):
    async def test_interruption_preserves_existing_agent_user_message(self) -> None:
        runner = AgentRunner.__new__(AgentRunner)
        runner._llm = Mock()
        runner._llm.query_agent = Mock(return_value=object())
        runner._ui = Mock()
        runner._ui.wait.return_value = nullcontext()
        runner._interrupt_coordinator = Mock()
        runner._interrupt_coordinator.run = AsyncMock(return_value=(True, None))

        await runner.process_query("Agent message")

        runner._llm.add_user_history.assert_called_once_with("Agent message")
        runner._ui.display_interrupted.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
