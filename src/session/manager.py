import os

from rich.console import Console

from src.commands.registry import COMMANDS
from src.commands.contracts import CommandResult, COMMAND_HANDLER_NAMES
from src.commands.processor import CommandProcessor
from src.db.vector_database import VectorDatabase
from src.db.min_hasher import MinHasher
from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis
from src.ingestion.ingestion_runner import IngestionRunner
from src.ingestion.semantic_chunker import SemanticChunker
from src.ingestion.pdf_parser import PdfParser
from src.ingestion.document_curator import DocumentCurator
from src.ingestion.metadata_extractor import MetadataExtractor
from src.retrieval.factory import create_reranker
from src.agent.agent_tools import AgentTools
from src.llm.chat_llm import ChatLLM
from src.llm.factory import create_llm_adapter
from src.llm.models import MODEL_OPTIONS, DEFAULT_CHAT_MODEL

from .chat_handlers import ChatHandlers
from .database_handlers import DatabaseHandlers
from .query_runner import QueryRunner
from .agent_runner import AgentRunner
from .reference_presenter import ReferencePresenter


class SessionManager:
    def __init__(self):
        self._console = Console()
        self._ui = AxonUI(self._console)

        self._llm_adapter = create_llm_adapter(DEFAULT_CHAT_MODEL, self._ui)
        self._llm = ChatLLM(self._ui, self._llm_adapter)

        self._metadata_extractor = MetadataExtractor(self._ui, self._llm_adapter)
        self._document_curator = DocumentCurator(self._ui, self._llm_adapter)
        self._parser = PdfParser(self._document_curator, self._metadata_extractor)
        self._chunker = SemanticChunker(self._console)
        self._db = VectorDatabase(self._console)
        self._minhasher = MinHasher()

        self._agent_mode_enabled = False

        self._reranker = create_reranker()
        self._init_session_components()
        self._init_command_processor()


    def _init_session_components(self) -> None:
        self._agent_tools = AgentTools(
            chunker=self._chunker,
            db=self._db,
            reranker=self._reranker,
        )

        self._ingestion_runner = IngestionRunner(
            parser=self._parser,
            chunker=self._chunker,
            db=self._db,
            minhasher=self._minhasher,
            ui=self._ui,
        )

        self._reference_presenter = ReferencePresenter(
            db=self._db,
            ui=self._ui,
        )

        self._chat_handlers = ChatHandlers(
            db=self._db,
            llm=self._llm,
            ui=self._ui,
        )

        self._database_handlers = DatabaseHandlers(
            db=self._db,
            ingestion_runner=self._ingestion_runner,
            ui=self._ui,
        )

        self._query_runner = QueryRunner(
            llm=self._llm,
            ui=self._ui,
            agent_tools=self._agent_tools,
            reference_presenter=self._reference_presenter,
        )

        self._agent_runner = AgentRunner(
            llm=self._llm,
            agent_tools=self._agent_tools,
            ui=self._ui,
            reference_presenter=self._reference_presenter,
        )


    def _init_cmd_handlers(self) -> None:
        self._command_handlers = {
            COMMAND_HANDLER_NAMES.SAVE_CHAT: self._chat_handlers.save_chat,
            COMMAND_HANDLER_NAMES.LOAD_CHAT: self._chat_handlers.load_chat,
            COMMAND_HANDLER_NAMES.CLEAR_CHAT: self._chat_handlers.clear_chat,
            COMMAND_HANDLER_NAMES.SET_LIMIT: self._chat_handlers.set_limit,
            COMMAND_HANDLER_NAMES.COMPACT: self._chat_handlers.compact,
            COMMAND_HANDLER_NAMES.AUTO_COMPACT: self._chat_handlers.auto_compact,
            COMMAND_HANDLER_NAMES.LIST_CHATS: self._chat_handlers.list_chats,
            COMMAND_HANDLER_NAMES.DELETE_CHAT: self._chat_handlers.delete_chat,
            COMMAND_HANDLER_NAMES.CHAT_ROLL: self._chat_handlers.chat_roll,

            COMMAND_HANDLER_NAMES.LOAD_PDFS: self._database_handlers.load_pdfs,
            COMMAND_HANDLER_NAMES.CLEAR_DB: self._database_handlers.clear_db,

            COMMAND_HANDLER_NAMES.CLEAR_SCREEN: self._clear_screen,
            COMMAND_HANDLER_NAMES.SELECT_MODEL: self._select_model,
            COMMAND_HANDLER_NAMES.EXIT: self._exit,
            COMMAND_HANDLER_NAMES.HELP: self._help,
            COMMAND_HANDLER_NAMES.TOGGLE_AGENT: self._toggle_agent,
        }

    def _init_command_processor(self) -> None:
        self._init_cmd_handlers()

        self._command_processor = CommandProcessor(
            commands=COMMANDS,
            handlers=self._command_handlers,
            ui=self._ui,
        )


    def _help(self) -> None:
        self._ui.display_help(COMMANDS)


    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")


    def _exit(self) -> CommandResult:
        self._ui.info("Shutting down Axon. Goodbye!")
        return CommandResult.EXIT


    def _toggle_agent(self) -> None:
        self._agent_mode_enabled = not self._agent_mode_enabled
        status = "on" if self._agent_mode_enabled else "off"
        self._ui.info(f"Agent Mode successfully toggled {emphasis(status)}!")


    def _select_model(self) -> None:
        selected_model = self._ui.select_option(MODEL_OPTIONS)

        self._llm_adapter = create_llm_adapter(selected_model, self._ui)
        self._llm.set_llm_adapter(self._llm_adapter)
        self._llm.set_chat_model(selected_model)

        self._ui.info(f"Using Model: {emphasis(selected_model)}")


    def run(self) -> None:
        should_exit = False
        while not should_exit:
            curr_tokens = self._llm.get_token_count()
            user_input = self._ui.listen(curr_tokens, self._llm.get_chat_limit())
            if not user_input:
                continue

            if user_input.startswith("/"):
                #TODO: When clear screen don't print cursor on new line
                should_exit = self._command_processor.process(user_input)
                continue

            if self._agent_mode_enabled:
                self._agent_runner.process_query(user_input)
                continue

            self._query_runner.process_query(user_input)
