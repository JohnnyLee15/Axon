from typing import Any

from src.llm.chat_llm import ChatLLM
from src.ui.axon_ui import AxonUI
from src.agent.agent_tools import AgentTools
from src.agent.tool_contracts import TOOL_NAMES, TOOL_RESULTS
from src.llm.contracts import LLM_CONTRACT
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.ui.formatters import emphasis
from src.ui.choices import CONFIRM_NO, CONFIRM_TRUST, CONFIRM_YES

from .reference_presenter import ReferencePresenter


class AgentRunner:
    def __init__(
        self,
        llm: ChatLLM,
        agent_tools: AgentTools,
        ui: AxonUI,
        reference_presenter: ReferencePresenter,
    ) -> None:
        self._llm = llm
        self._agent_tools = agent_tools
        self._ui = ui
        self._reference_presenter = reference_presenter

        self._init_tools()


    def _init_tools(self) -> None:
        self._trusted_tools = set()
        self._tool_functions = {
            TOOL_NAMES.SEARCH_FOR_CHUNKS: self._agent_tools.search_for_chunks,
            TOOL_NAMES.EXECUTE_BASH_CMD: self._agent_tools.execute_bash_cmd,
            TOOL_NAMES.CREATE_FILE: self._agent_tools.create_file,
            TOOL_NAMES.REPLACE_IN_FILE: self._agent_tools.replace_in_file,
            TOOL_NAMES.READ_FILE: self._agent_tools.read_file,
            TOOL_NAMES.INSERT_TO_FILE: self._agent_tools.insert_to_file
        }


    def _record_tool_denial(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        self._llm.add_function_call_history(tool_name, tool_args)
        self._llm.add_function_response_history(
            tool_name,
            (
                f"User denied permission to execute {tool_name} this time. "
                "Respond without this tool if possible or try to use another tool. "
                "Do not claim you are unable to help just because this tool was denied."
            )
        )


    def _record_tool_interruption(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        user_input: str
    ) -> None:
        self._llm.add_function_call_history(tool_name, tool_args)
        self._llm.add_function_response_history(
            tool_name,
            f"User interrupted execution of {tool_name} with a new message instead."
        )
        self._llm.add_user_history(user_input)


    def _confirm_tool_use(self, tool_name: str, tool_args: dict[str, Any]) -> bool:
        choice_descriptions = (
            f"{emphasis(CONFIRM_YES)} = yes once | "
            f"{emphasis(CONFIRM_TRUST)} = trust for session | "
            f"{emphasis(CONFIRM_NO)} = no"
        )
        choice_raw = self._ui.confirm(
            f"Agent wants to use tool {emphasis(tool_name)}. "
            f"Allow? {choice_descriptions}: "
        ).strip()
        choice = choice_raw.lower()

        if choice == CONFIRM_TRUST:
            self._trusted_tools.add(tool_name)
            return True

        if choice == CONFIRM_YES:
            return True

        if choice == CONFIRM_NO:
            self._record_tool_denial(tool_name, tool_args)
            return False

        self._record_tool_interruption(tool_name, tool_args, choice_raw)
        return False


    def _record_unavailable_tool(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        self._llm.add_function_call_history(tool_name, tool_args)
        self._llm.add_function_response_history(
            tool_name,
            f"Tool '{tool_name}' is not available."
        )


    def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        self._ui.progress(f"Agent executing: {emphasis(tool_name)}.")
        with self._ui.wait():
            results = self._tool_functions[tool_name](**tool_args)

        self._ui.display_tool_output(tool_name, results)

        result_content = results[TOOL_RESULTS.CONTENT] or "No results returned"
        self._llm.add_function_call_history(tool_name, tool_args)
        self._llm.add_function_response_history(tool_name, result_content)

        return results


    def _handle_tool_call(
        self,
        tool_call: dict[str, Any]
    ) -> dict[int, dict[str, str | int]]:
        tool_name = tool_call[LLM_CONTRACT.NAME]
        tool_args = tool_call[LLM_CONTRACT.ARGS]

        if tool_name not in self._tool_functions:
            self._record_unavailable_tool(tool_name, tool_args)
            return {}

        self._ui.display_tool_args(tool_name, tool_args)
        if tool_name not in self._trusted_tools:
            proceed = self._confirm_tool_use(tool_name, tool_args)
            if not proceed:
                return {}

        results = self._execute_tool(tool_name, tool_args)
        return results.get(TOOL_RESULTS.RAW_CHUNKS) or {}


    def _finish_response(
        self,
        response: dict[str, Any],
        retrieved_chunks: dict[int, dict[str, str | int]]
    ) -> None:
        response_text = response[LLM_CONTRACT.TEXT]

        if not response_text:
            self._ui.success("Agent task completed.")
            return

        self._llm.add_model_history(response_text)
        self._ui.stream_response(response_text)
        self._reference_presenter.display_references(retrieved_chunks)


    def process_query(self, user_input: str) -> None:
        self._llm.add_user_history(user_input)
        retrieved_chunks = {}
        agent_running = True

        while agent_running:
            with self._ui.wait():
                response = self._llm.query_agent(TOOL_SCHEMAS)

            if not response:
                return

            tool_calls = response[LLM_CONTRACT.TOOL_CALLS]
            if tool_calls:
                raw_chunks = self._handle_tool_call(tool_calls[0])
                retrieved_chunks.update(raw_chunks)
            else:
                agent_running = False

        self._finish_response(response, retrieved_chunks)