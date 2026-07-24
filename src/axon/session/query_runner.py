from axon.ui.axon_ui import AxonUI
from axon.llm.chat_llm import ChatLLM
from axon.agent.library_search_tool import LibrarySearchTool
from axon.agent.tool_contracts import TOOL_NAMES, TOOL_ARGS, TOOL_RESULTS

from .reference_presenter import ReferencePresenter


class QueryRunner:
    def __init__(
        self,
        llm: ChatLLM,
        ui: AxonUI,
        library_search_tool: LibrarySearchTool,
        reference_presenter: ReferencePresenter,
    ) -> None:
        self._llm = llm
        self._ui = ui
        self._library_search_tool = library_search_tool
        self._reference_presenter = reference_presenter


    def process_query(self, user_input: str) -> None:
        search_query = self._llm.rewrite_query(user_input)
        self._ui.display_tool_args(
            TOOL_NAMES.SEARCH_LIBRARY,
            {TOOL_ARGS.QUERY: search_query}
        )

        with self._ui.wait():
            results = self._library_search_tool.search_library(search_query)

        self._ui.display_tool_output(TOOL_NAMES.SEARCH_LIBRARY, results)
        with self._ui.wait():
            response = self._llm.query_chat(user_input, results[TOOL_RESULTS.CONTENT])

        if response:
            self._ui.stream_response(response)
            self._reference_presenter.display_references(results[TOOL_RESULTS.RAW_CHUNKS])
