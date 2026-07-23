import os

from dotenv import load_dotenv

from src.commands.registry import COMMANDS
from src.commands.contracts import CommandResult, COMMAND_HANDLER_NAMES
from src.commands.processor import CommandProcessor

from src.db.sqlite_database import SQLiteDatabase
from src.db.chat_repository import ChatRepository
from src.db.chunk_repository import ChunkRepository
from src.db.paper_repository import PaperRepository
from src.db.schema_manager import SchemaManager
from src.db.min_hasher import MinHasher

from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis

from src.ingestion.ingestion_runner import IngestionRunner
from src.ingestion.semantic_chunker import SemanticChunker
from src.ingestion.pdf_parser import PdfParser
from src.ingestion.document_curator import DocumentCurator
from src.ingestion.metadata_extractor import MetadataExtractor
from src.ingestion.torch_embedding_backend import TorchEmbeddingBackend

from src.retrieval.factory import create_reranker

from src.agent.agent_tools import AgentTools

from src.utils.paths import ENV_PATH

from src.llm.chat_llm import ChatLLM
from src.llm.factory import create_llm_adapter
from src.llm.models import MODEL_OPTIONS, DEFAULT_CHAT_MODEL

from .chat_handlers import ChatHandlers
from .library_handlers import LibraryHandlers
from .query_runner import QueryRunner
from .agent_runner import AgentRunner
from .reference_presenter import ReferencePresenter


class SessionManager:
    def __init__(self):
        load_dotenv(ENV_PATH)
        self._ui = AxonUI()
        self._agent_mode_enabled = False

        self._init_database()
        self._init_llm()
        self._init_ingestion()
        self._init_session_services()
        self._init_command_processor()


    def _init_database(self) -> None:
        self._database = SQLiteDatabase()

        self._schema_manager = SchemaManager(self._database)
        self._schema_manager.initialize()

        self._chat_repository = ChatRepository(self._database)
        self._chunk_repository = ChunkRepository(self._database)
        self._paper_repository = PaperRepository(self._database)


    def _init_llm(self) -> None:
        self._llm_adapter = create_llm_adapter(DEFAULT_CHAT_MODEL, self._ui)
        self._llm = ChatLLM(self._ui, self._llm_adapter)


    def _init_ingestion(self) -> None:
        self._metadata_extractor = MetadataExtractor(self._ui, self._llm_adapter)
        self._document_curator = DocumentCurator(self._ui, self._llm_adapter)
        self._parser = PdfParser(self._document_curator, self._metadata_extractor)
        self._chunker = SemanticChunker()
        self._embedding_backend = TorchEmbeddingBackend()
        self._minhasher = MinHasher()
        self._ingestion_runner = IngestionRunner(
            parser=self._parser,
            chunker=self._chunker,
            embedding_backend=self._embedding_backend,
            chunk_repository=self._chunk_repository,
            paper_repository=self._paper_repository,
            minhasher=self._minhasher,
            ui=self._ui,
        )

    def _init_session_services(self) -> None:
        self._reranker = create_reranker()

        self._agent_tools = AgentTools(
            embedding_backend=self._embedding_backend,
            chunk_repository=self._chunk_repository,
            reranker=self._reranker,
        )

        self._reference_presenter = ReferencePresenter(
            paper_repository=self._paper_repository,
            ui=self._ui,
        )

        self._chat_handlers = ChatHandlers(
            chat_repository=self._chat_repository,
            llm=self._llm,
            ui=self._ui,
        )

        self._library_handlers = LibraryHandlers(
            paper_repository=self._paper_repository,
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

            COMMAND_HANDLER_NAMES.LOAD_PDFS: self._library_handlers.load_pdfs,
            COMMAND_HANDLER_NAMES.CLEAR_LIBRARY: self._library_handlers.clear_library,

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
