from axon.commands.registry import COMMANDS
from axon.commands.contracts import CommandResult, COMMAND_HANDLER_NAMES
from axon.commands.processor import CommandProcessor

from axon.db.sqlite_database import SQLiteDatabase
from axon.db.chat_repository import ChatRepository
from axon.db.chunk_repository import ChunkRepository
from axon.db.paper_repository import PaperRepository
from axon.db.schema_manager import SchemaManager
from axon.db.min_hasher import MinHasher

from axon.ui.axon_ui import AxonUI
from axon.ui.formatters import emphasis
from axon.ui.contracts import OPTION_KEY

from axon.ingestion.ingestion_runner import IngestionRunner
from axon.ingestion.semantic_chunker import SemanticChunker
from axon.ingestion.pdf_parser import PdfParser
from axon.ingestion.document_curator import DocumentCurator
from axon.ingestion.metadata_extractor import MetadataExtractor
from axon.ingestion.torch_embedding_backend import TorchEmbeddingBackend

from axon.retrieval.factory import create_reranker

from axon.agent.library_search_tool import LibrarySearchTool

from axon.llm.chat_llm import ChatLLM
from axon.llm.llm_adapter import LLMAdapter
from axon.llm.models import DEFAULT_CHAT_MODEL
from axon.llm.settings import DEFAULT_CONTEXT_SIZE

from axon.config.settings_store import (
    CHAT_LIMIT_KEY,
    CHAT_MODEL_KEY,
    SettingsStore,
)

from .chat_handlers import ChatHandlers
from .library_handlers import LibraryHandlers
from .query_runner import QueryRunner
from .agent_runner import AgentRunner
from .reference_presenter import ReferencePresenter
from .options import CHAT_LIMIT_OPTIONS, MODEL_OPTIONS
from .interrupt_coordinator import InterruptCoordinator


class SessionManager:
    def __init__(
        self,
        ui: AxonUI,
        llm_adapter: LLMAdapter,
        settings: SettingsStore,
    ):
        self._agent_mode_enabled = False
        self._settings = settings
        self._ui = ui
        self._llm_adapter = llm_adapter

        self._interrupt_coordinator = InterruptCoordinator(self._ui)
        self._llm = ChatLLM(
            ui=self._ui,
            llm_adapter=self._llm_adapter,
            chat_model=self._get_saved_chat_model(),
            context_size=self._get_saved_chat_limit(),
        )

        self._init_database()
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

        self._library_search_tool = LibrarySearchTool(
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
            settings=self._settings,
            interrupt_coordinator=self._interrupt_coordinator,
        )

        self._library_handlers = LibraryHandlers(
            paper_repository=self._paper_repository,
            ingestion_runner=self._ingestion_runner,
            ui=self._ui,
        )

        self._query_runner = QueryRunner(
            llm=self._llm,
            ui=self._ui,
            library_search_tool=self._library_search_tool,
            reference_presenter=self._reference_presenter,
            interrupt_coordinator=self._interrupt_coordinator,
        )

        self._agent_runner = AgentRunner(
            llm=self._llm,
            library_search_tool=self._library_search_tool,
            ui=self._ui,
            reference_presenter=self._reference_presenter,
            interrupt_coordinator=self._interrupt_coordinator,
        )


    def _init_cmd_handlers(self) -> None:
        self._command_handlers = {
            COMMAND_HANDLER_NAMES.SAVE_CHAT: self._chat_handlers.save_chat,
            COMMAND_HANDLER_NAMES.LOAD_CHAT: self._chat_handlers.load_chat,
            COMMAND_HANDLER_NAMES.CLEAR_CHAT: self._chat_handlers.clear_chat,
            COMMAND_HANDLER_NAMES.DISPLAY_HISTORY: self._chat_handlers.display_history,
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


    def _get_saved_chat_model(self) -> str:
        model_options = [option[OPTION_KEY] for option in MODEL_OPTIONS]
        saved_model = self._settings.get(CHAT_MODEL_KEY)
        if saved_model in model_options:
            return saved_model

        return DEFAULT_CHAT_MODEL


    def _get_saved_chat_limit(self) -> int:
        chat_limit_options = [option[OPTION_KEY] for option in CHAT_LIMIT_OPTIONS]
        saved_limit = self._settings.get(CHAT_LIMIT_KEY)
        if saved_limit in chat_limit_options:
            return saved_limit

        return DEFAULT_CONTEXT_SIZE


    def _help(self) -> None:
        self._ui.display_help(COMMANDS)


    def _clear_screen(self) -> None:
        self._ui.clear_screen()


    def _exit(self) -> CommandResult:
        self._ui.display_goodbye()
        return CommandResult.EXIT


    def _toggle_agent(self) -> None:
        self._agent_mode_enabled = not self._agent_mode_enabled
        status = "on" if self._agent_mode_enabled else "off"
        self._ui.info(f"Agent Mode successfully toggled {emphasis(status)}!")


    async def _select_model(self) -> None:
        selected_model = await self._ui.select_item(
            options=MODEL_OPTIONS,
            selected_option=self._llm.get_chat_model(),
        )

        if selected_model is None:
            return

        self._llm.set_chat_model(selected_model)
        self._settings.set(key=CHAT_MODEL_KEY, value=selected_model)
        self._ui.info(f"Using Model: {emphasis(selected_model)}")


    async def run(self) -> None:
        should_exit = False
        while not should_exit:
            curr_tokens = await self._llm.get_token_count()
            user_input = await self._ui.listen(
                curr_tokens=curr_tokens,
                context_size=self._llm.get_chat_limit(),
                model_name=self._llm.get_chat_model(),
            )
            if not user_input:
                continue

            if user_input.startswith("/"):
                should_exit = await self._command_processor.process(user_input)
                continue

            if not self._agent_mode_enabled:
                await self._query_runner.process_query(user_input)
                continue

            await self._agent_runner.process_query(user_input)
