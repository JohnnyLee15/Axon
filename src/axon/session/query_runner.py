import time

from axon.ui.axon_ui import AxonUI
from axon.llm.chat_llm import ChatLLM
from axon.agent.library_search_tool import LibrarySearchTool
from axon.agent.tool_contracts import TOOL_NAMES, TOOL_ARGS, TOOL_RESULTS

from .reference_presenter import ReferencePresenter
from .interrupt_coordinator import InterruptCoordinator


class QueryRunner:
    def __init__(
        self,
        llm: ChatLLM,
        ui: AxonUI,
        library_search_tool: LibrarySearchTool,
        reference_presenter: ReferencePresenter,
        interrupt_coordinator: InterruptCoordinator,
    ) -> None:
        self._llm = llm
        self._ui = ui
        self._library_search_tool = library_search_tool
        self._reference_presenter = reference_presenter
        self._interrupt_coordinator = interrupt_coordinator


    def _handle_interruption(self, user_input: str) -> None:
        self._llm.add_user_history(user_input)
        self._ui.display_interrupted()


    async def process_query(self, user_input: str) -> None:
        started_at = time.monotonic()

        with self._ui.wait(
            show_cancel_hint=True,
            started_at=started_at,
        ):
            interrupted, search_query = await self._interrupt_coordinator.run(
                self._llm.rewrite_query(user_input)
            )

        if interrupted:
            self._handle_interruption(user_input)
            return

        self._ui.display_tool_args(
            TOOL_NAMES.SEARCH_LIBRARY,
            {TOOL_ARGS.QUERY: search_query}
        )

        with self._ui.wait(started_at=started_at):
            results = self._library_search_tool.search_library(search_query)

        self._ui.display_tool_output(TOOL_NAMES.SEARCH_LIBRARY, results)

        with self._ui.wait(
            show_cancel_hint=True,
            started_at=started_at,
        ):
            interrupted, response = await self._interrupt_coordinator.run(
                self._llm.query_chat(user_input, results[TOOL_RESULTS.CONTENT])
            )

        if interrupted:
            self._handle_interruption(user_input)
            return

        if not response:
            return

        total_seconds = int(time.monotonic() - started_at)
        self._ui.display_work_duration(total_seconds)
        self._ui.stream_response(response)
        self._reference_presenter.display_references(results[TOOL_RESULTS.RAW_CHUNKS])
