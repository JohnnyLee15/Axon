from typing import Any
import time

from axon.llm.chat_llm import ChatLLM
from axon.llm.contracts import LLM_CONTRACT
from axon.ui.axon_ui import AxonUI
from axon.ui.formatters import emphasis
from axon.ui.choices import CONFIRM_NO, CONFIRM_TRUST, CONFIRM_YES
from axon.agent.tool_contracts import TOOL_NAMES, TOOL_RESULTS
from axon.agent.tool_schemas import TOOL_SCHEMAS
from axon.agent.shell_tools import execute_shell_cmd
from axon.agent.library_search_tool import LibrarySearchTool
from axon.agent.file_tools import (
    create_file,
    insert_to_file,
    read_file,
    replace_in_file,
)

from .reference_presenter import ReferencePresenter
from .interrupt_coordinator import InterruptCoordinator


class AgentRunner:
    def __init__(
        self,
        llm: ChatLLM,
        library_search_tool: LibrarySearchTool,
        ui: AxonUI,
        reference_presenter: ReferencePresenter,
        interrupt_coordinator: InterruptCoordinator,
    ) -> None:
        self._llm = llm
        self._library_search_tool = library_search_tool
        self._ui = ui
        self._reference_presenter = reference_presenter
        self._interrupt_coordinator = interrupt_coordinator

        self._init_tools()


    def _init_tools(self) -> None:
        self._trusted_tools = set()
        self._tool_functions = {
            TOOL_NAMES.SEARCH_LIBRARY: self._library_search_tool.search_library,
            TOOL_NAMES.EXECUTE_SHELL_CMD: execute_shell_cmd,
            TOOL_NAMES.CREATE_FILE: create_file,
            TOOL_NAMES.REPLACE_IN_FILE: replace_in_file,
            TOOL_NAMES.READ_FILE: read_file,
            TOOL_NAMES.INSERT_TO_FILE: insert_to_file,
        }


    def _record_tool_denial(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        provider_metadata: dict[str, Any] | None,
    ) -> None:
        self._llm.add_tool_call_history(
            tool_name,
            tool_args,
            provider_metadata,
        )
        self._llm.add_tool_response_history(
            tool_name,
            (
                f"User denied permission to execute {tool_name} this time. "
                "Respond without this tool if possible or try to use another tool. "
                "Do not claim you are unable to help just because this tool was denied."
            ),
            provider_metadata,
        )


    def _record_tool_interruption(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        user_input: str,
        provider_metadata: dict[str, Any] | None,
    ) -> None:
        self._llm.add_tool_call_history(
            tool_name,
            tool_args,
            provider_metadata,
        )
        self._llm.add_tool_response_history(
            tool_name,
            f"User interrupted execution of {tool_name} with a new message instead.",
            provider_metadata,
        )
        self._llm.add_user_history(user_input)


    def _confirm_tool_use(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        provider_metadata: dict[str, Any] | None,
    ) -> bool:
        choice_descriptions = (
            f"{emphasis(CONFIRM_YES)} = yes once | "
            f"{emphasis(CONFIRM_TRUST)} = trust for session | "
            f"{emphasis(CONFIRM_NO)} = no"
        )
        choice_raw = self._ui.confirm(
            f"Agent wants to use tool {emphasis(tool_name)}. "
            f"Allow? {choice_descriptions}"
        ).strip()
        choice = choice_raw.lower()

        if choice == CONFIRM_TRUST:
            self._trusted_tools.add(tool_name)
            return True

        if choice == CONFIRM_YES:
            return True

        if choice == CONFIRM_NO:
            self._record_tool_denial(
                tool_name,
                tool_args,
                provider_metadata,
            )
            return False

        self._record_tool_interruption(
            tool_name,
            tool_args,
            choice_raw,
            provider_metadata,
        )
        return False


    def _record_unavailable_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        provider_metadata: dict[str, Any] | None,
    ) -> None:
        self._llm.add_tool_call_history(
            tool_name,
            tool_args,
            provider_metadata,
        )
        self._llm.add_tool_response_history(
            tool_name,
            f"Tool '{tool_name}' is not available.",
            provider_metadata,
        )


    def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        provider_metadata: dict[str, Any] | None,
        started_at: float,
    ) -> dict[str, Any]:
        self._ui.progress(f"Agent executing: {emphasis(tool_name)}.")

        with self._ui.wait(started_at=started_at):
            results = self._tool_functions[tool_name](**tool_args)

        self._ui.display_tool_output(tool_name, results)

        result_content = results[TOOL_RESULTS.CONTENT] or "No results returned"
        self._llm.add_tool_call_history(
            tool_name,
            tool_args,
            provider_metadata,
        )
        self._llm.add_tool_response_history(
            tool_name,
            result_content,
            provider_metadata,
        )

        return results


    def _handle_tool_call(
        self,
        tool_call: dict[str, Any],
        started_at: float,
    ) -> dict[int, dict[str, str | int]]:
        tool_name = tool_call[LLM_CONTRACT.NAME]
        tool_args = tool_call[LLM_CONTRACT.ARGS]
        provider_metadata = tool_call.get(LLM_CONTRACT.PROVIDER_METADATA)

        if tool_name not in self._tool_functions:
            self._record_unavailable_tool(
                tool_name,
                tool_args,
                provider_metadata,
            )
            return {}

        self._ui.display_tool_args(tool_name, tool_args)
        if tool_name not in self._trusted_tools:
            proceed = self._confirm_tool_use(
                tool_name,
                tool_args,
                provider_metadata,
            )
            if not proceed:
                return {}

        results = self._execute_tool(
            tool_name,
            tool_args,
            provider_metadata,
            started_at,
        )
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


    async def process_query(self, user_input: str) -> None:
        started_at = time.monotonic()

        self._llm.add_user_history(user_input)
        retrieved_chunks = {}
        agent_running = True

        while agent_running:
            with self._ui.wait(
                show_cancel_hint=True,
                started_at=started_at,
            ):
                interrupted, response = await self._interrupt_coordinator.run(
                    self._llm.query_agent(TOOL_SCHEMAS)
                )

            if interrupted:
                self._ui.display_interrupted()
                return

            if not response:
                return

            tool_calls = response[LLM_CONTRACT.TOOL_CALLS]
            if tool_calls:
                raw_chunks = self._handle_tool_call(tool_calls[0], started_at)
                retrieved_chunks.update(raw_chunks)
            else:
                agent_running = False

        total_seconds = int(time.monotonic() - started_at)
        self._ui.display_work_duration(total_seconds)
        self._finish_response(response, retrieved_chunks)
