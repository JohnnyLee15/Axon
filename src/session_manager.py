from rich.console import Console
from typing import Any
import os
import time
from pathlib import Path

from src.ingestion.semantic_chunker import SemanticChunker
from src.ingestion.pdf_parser import PdfParser
from src.db.vector_database import VectorDatabase
from src.ui.axon_ui import AxonUI
from src.llm.chat_llm import ChatLLM
from src.db.min_hasher import MinHasher
from src.utils.config import *
from src.retrieval.mlx_chunk_reranker import MLXChunkReranker
from src.retrieval.torch_chunk_reranker import TorchChunkReranker
from src.utils.device_utils import get_torch_device
from src.agent.agent_tools import AgentTools
from src.llm.llm_factory import create_llm_adapter

class SessionManager:
    def __init__(self):
        self._console = Console()
        self._llm_adapter = create_llm_adapter(LLM_CHAT_MODEL_DEFAULT, self._console)
        self._parser = PdfParser(self._console, self._llm_adapter)
        self._chunker = SemanticChunker(self._console)
        self._db = VectorDatabase(self._console)
        self._ui = AxonUI(self._console)
        self._llm = ChatLLM(self._console, self._llm_adapter)
        self._minhasher = MinHasher()
        self._agent_mode_enabled = False
        self._init_reranker()
        self._init_cmds()
        self._init_agent()


    def _init_agent(self) -> None:
        self._trusted_tools = set()
        self._agent_tools = AgentTools(self._chunker, self._db, self._reranker)
        self._tool_functions = {
            "search_for_chunks": self._agent_tools.search_for_chunks,
            "execute_bash_cmd": self._agent_tools.execute_bash_cmd,
            "create_file": self._agent_tools.create_file,
            "replace_in_file": self._agent_tools.replace_in_file,
            "read_file": self._agent_tools.read_file,
            "insert_to_file": self._agent_tools.insert_to_file
        }


    def _init_reranker(self) -> None:
        device = get_torch_device()

        if device.type == "mps":
            self._reranker = MLXChunkReranker()
        else:
            self._reranker = TorchChunkReranker()


    def _init_cmd_handlers(self) -> None:
        self._command_handlers = {
            "save_chat": self._chat_commands.save_chat,
            "load_chat": self._chat_commands.load_chat,
            "clear_chat": self._chat_commands.clear_chat,
            "set_limit": self._chat_commands.set_limit,
            "compact": self._chat_commands.compact,
            "auto_compact": self._chat_commands.auto_compact,
            "list_chats": self._chat_commands.list_chats,
            "delete_chat": self._chat_commands.delete_chat,
            "chat_roll": self._chat_commands.chat_roll,

            "load_pdfs": self._db_commands.load_pdfs,
            "clear_db": self._db_commands.clear_db,

            "clear_screen": self._clear_screen,
            "select_model": self._select_model,
            "exit": self._exit,
            "help": self._help,
            "toggle_agent": self._toggle_agent,
        }


    def _help(self) -> None:
        self._ui.display_help(self._COMMANDS)


    def _clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")


    def _exit(self):
        self._console.print("\n👋 [bold]Shutting down Axon. Goodbye![/bold]")
        return True


    def _toggle_agent(self):
        self._agent_mode_enabled = not self._agent_mode_enabled
        status = "on" if self._agent_mode_enabled else "off"
        self._console.print(f"\n🧠 [bold]Agent Mode successfully toggled [cyan]{status}[/cyan]![/bold]")


    def _select_model(self) -> None:
        selected_model = self._select_item_from_id_dict(LLMS)

        self._llm_adapter = create_llm_adapter(selected_model, self._console)
        self._llm.set_llm_adapter(self._llm_adapter)
        self._llm.set_chat_llm(selected_model)

        self._console.print(f"\n🤖 [bold]Using Model:[/bold] {selected_model}")


    def _display_references(self, chunks: dict[int, dict[str, str | int]]):
        if not chunks:
            return

        paper_ids = set()
        for chunk in chunks.values():
            paper_ids.add(chunk["paper_id"])

        paper_properties = self._db.get_paper_metadata_by_id(list(paper_ids))
        if not paper_properties:
            return

        self._ui.display_references(paper_properties)


    def _process_query_without_agent(self, user_input: str) -> None:
        search_query = self._llm.rewrite_query(user_input)
        self._ui.display_tool_args("search_for_chunks", {"query": search_query})
        with self._ui.wait():
            results = self._agent_tools.search_for_chunks(search_query)

        self._ui.display_tool_output("search_for_chunks", results)
        with self._ui.wait():
            response = self._llm.query_chat(user_input, results["content"])

        if response:
            self._ui.stream_response(response)
            self._display_references(results["raw_chunks"])


    def _confirm_tool_use(self, tool_name: str, tool_args: dict) -> bool:
        self._console.print(
            f"\n🔐 [bold][yellow]Agent wants to use tool[/yellow] "
            f"[cyan]{tool_name}[/cyan][/bold]"
        )
        self._console.print(
            "[bold]Allow? [cyan]y[/cyan] = yes once, "
            "[cyan]t[/cyan] = trust for session, "
            "[cyan]n[/cyan] = no[/bold]"
        )

        choice_raw = self._console.input("❓ [bold]Choice ([cyan]y/t/n[/cyan]): [/bold]").strip()
        choice = choice_raw.lower()
        if choice == "t":
            self._trusted_tools.add(tool_name)
            return True

        if choice == "y":
            return True

        if choice == "n":
            self._llm.add_function_call_history(tool_name, tool_args)
            self._llm.add_function_response_history(
                tool_name,
                (
                    f"User denied permission to execute {tool_name} this time. "
                    "Respond without this tool if possible or try to use another tool. "
                    "Do not claim you are unable to help just because this tool was denied."
                )
            )
            return False

        self._llm.add_function_call_history(tool_name, tool_args)
        self._llm.add_function_response_history(
            tool_name,
            f"User interrupted execution of {tool_name} with a new message instead."
        )
        self._llm.add_user_history(choice_raw)
        return False



    def _process_query_with_agent(self, user_input: str) -> None:
        self._llm.add_user_history(user_input)
        retrieved_chunks = {}
        agent_running = True

        while agent_running:
            with self._ui.wait():
                response = self._llm.query_agent(TOOL_SCHEMAS)

            if not response:
                return

            tool_calls = response["tool_calls"]
            if tool_calls:
                call = tool_calls[0]
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name not in self._tool_functions:
                    self._llm.add_function_call_history(tool_name, tool_args)
                    self._llm.add_function_response_history(
                        tool_name,
                        f"Tool '{tool_name}' is not available."
                    )
                    continue

                self._ui.display_tool_args(tool_name, tool_args)
                if tool_name not in self._trusted_tools:
                    proceed = self._confirm_tool_use(tool_name, tool_args)
                    if not proceed:
                        continue

                self._console.print(f"\n🤖 Agent executing: {tool_name}")
                with self._ui.wait():
                    results = self._tool_functions[tool_name](**tool_args)

                llm_content = results["content"]
                if results.get("raw_chunks"):
                    retrieved_chunks.update(results["raw_chunks"])

                self._ui.display_tool_output(tool_name, results)
                result_for_history = llm_content or "No results returned"
                self._llm.add_function_call_history(tool_name, tool_args)
                self._llm.add_function_response_history(tool_name, result_for_history)
                continue

            agent_running = False

        response_text = response["text"]
        if response_text:
            self._llm.add_model_history(response_text)
            self._ui.stream_response(response_text)
            self._display_references(retrieved_chunks)
        else:
            self._console.print("\n✅ [bold]Agent task completed.[/bold]")


    def run(self) -> None:
        done = False
        while not done:
            curr_tokens = self._llm.get_token_count()
            user_input = self._ui.listen(curr_tokens, self._llm.get_chat_limit())
            if not user_input:
                continue

            if user_input.startswith("/"):
                #TODO: When clear screen don't print cursor on new line
                done = self._process_cmd(user_input)
                continue

            if self._agent_mode_enabled:
                self._process_query_with_agent(user_input)
                continue

            self._process_query_without_agent(user_input)




