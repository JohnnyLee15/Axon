import unittest
from contextlib import nullcontext
from unittest.mock import Mock

from axon.agent.tool_contracts import TOOL_RESULTS
from axon.llm.contracts import LLM_CONTRACT
from axon.session.agent_runner import AgentRunner


class ToolMetadataTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_records_provider_metadata_with_call_and_response(
        self,
    ) -> None:
        metadata = {
            "gemini": {
                "function_call_id": "call-123",
                "thought_signature": "c2lnbmF0dXJl",
            }
        }
        tool_name = "test_tool"
        tool_args = {"value": 1}
        runner = AgentRunner.__new__(AgentRunner)
        runner._trusted_tools = {tool_name}
        runner._tool_functions = {
            tool_name: lambda **kwargs: {TOOL_RESULTS.CONTENT: "complete"}
        }
        runner._llm = Mock()
        runner._ui = Mock()
        runner._ui.wait.return_value = nullcontext()

        results = await runner._handle_tool_call(
            {
                LLM_CONTRACT.NAME: tool_name,
                LLM_CONTRACT.ARGS: tool_args,
                LLM_CONTRACT.PROVIDER_METADATA: metadata,
            },
            started_at=0.0,
        )

        runner._llm.add_tool_call_history.assert_called_once_with(
            tool_name,
            tool_args,
            metadata,
        )
        runner._llm.add_tool_response_history.assert_called_once_with(
            tool_name,
            "complete",
            metadata,
        )
        self.assertEqual(results, {TOOL_RESULTS.CONTENT: "complete"})


if __name__ == "__main__":
    unittest.main()
