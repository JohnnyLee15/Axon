from src.ui.axon_ui import AxonUI
from src.llm.chat_llm import ChatLLM
from src.agent.agent_tools import AgentTools
from src.agent.tool_contracts import TOOL_NAMES, TOOL_ARGS, TOOL_RESULTS

from .reference_presenter import ReferencePresenter


class QueryRunner:
    def __init__(
        self,
        llm: ChatLLM,
        ui: AxonUI,
        agent_tools: AgentTools,
        reference_presenter: ReferencePresenter,
    ) -> None:
        self._llm = llm
        self._ui = ui
        self._agent_tools = agent_tools
        self._reference_presenter = reference_presenter


    def process_query(self, user_input: str) -> None:
        search_query = self._llm.rewrite_query(user_input)
        self._ui.display_tool_args(
            TOOL_NAMES.SEARCH_FOR_CHUNKS,
            {TOOL_ARGS.QUERY: search_query}
        )

        with self._ui.wait():
            results = self._agent_tools.search_for_chunks(search_query)

        self._ui.display_tool_output(TOOL_NAMES.SEARCH_FOR_CHUNKS, results)
        with self._ui.wait():
            response = self._llm.query_chat(user_input, results[TOOL_RESULTS.CONTENT])

        if response:
            self._ui.stream_response(response)
            self._reference_presenter.display_references(results[TOOL_RESULTS.RAW_CHUNKS])
