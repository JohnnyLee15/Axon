from rich.console import Console
from typing import Any
import os
import sqlite3
import time
from pathlib import Path

from src.ingestion.semantic_chunker import SemanticChunker
from src.ingestion.pdf_parser import PdfParser
from src.db.vector_database import VectorDatabase
from src.ui.axon_ui import AxonUI
from src.llm.chat_llm import ChatLLM
from src.db.min_hasher import MinHasher
from src.utils.paper_utils import get_active_ids
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


    def _init_cmds(self) -> None:
        self._CHAT_COMMANDS = {
            "save": {
                "usage": "/chat save <chat name> [-f]",
                "desc": "Saves the current chat history to disk. use -f to overwrite.",
                "argc": [1,2],
                "run": self._save_chat
            },
            "load": {
                "usage": "/chat load <chat name>",
                "desc": "Loads a previously saved chat history.",
                "argc": 1,
                "run": self._load_chat
            },
            "clear": {
                "usage": "/chat clear",
                "desc": "Clears the current chat history.",
                "argc": 0,
                "run": self._clear_chat
            },
            "limit": {
                "usage": "/chat limit",
                "desc": "Sets the context window size.",
                "argc": 0,
                "run": self._set_limit
            },
            "compact": {
                "usage": "/chat compact",
                "desc": "Replaces the current chat history with a condensed summary.",
                "argc": 0,
                "run": self._compact
            },
            "auto-compact": {
                "usage": "/chat auto-compact",
                "desc": "Toggles automatic chat history summarization when the context limit is hit.",
                "argc": 0,
                "run": self._auto_compact
            },
            "list": {
                "usage": "/chat list",
                "desc": "List all chats saved in the database.",
                "argc": 0,
                "run": self._list_chats
            },
            "delete": {
                "usage": "/chat delete <chat name> [-a]",
                "desc": "Deletes a saved chat from the database. Use -a to delete all chats.",
                "argc": 1,
                "run":self._delete_chat
            },
            "roll": {
                "usage": "/chat roll",
                "desc": "Toggles a rolling window that keeps the last 5 user-model chat pairs.",
                "argc": 0,
                "run": self._chat_roll
            }
        }

        self._DB_COMMANDS = {
            "load": {
                "usage": "/db load <file path>",
                "desc": "Loads a file or folder (and subfolders) of PDFs into the database.",
                "argc": 1,
                "run": self._load_pdfs
            },
            "clear": {
                "usage": "/db clear",
                "desc": "Remove all data from the database.",
                "argc": 0,
                "run": self._clear_db
            }
        }

        self._COMMANDS = {
            "chat": {
                "subcommands": self._CHAT_COMMANDS
            },
            "db": {
                "subcommands": self._DB_COMMANDS
            },
            "clear": {
                "usage": "/clear",
                "desc": "Clears the terminal screen.",
                "argc": 0,
                "run": self._clear_screen
            },
            "model": {
                "usage": "/model",
                "desc": "Sets the chat LLM model.",
                "argc": 0,
                "run": self._select_model
            },
            "exit": {
                "usage": "/exit",
                "desc": "Safely shuts down Axon and exits.",
                "argc": 0,
                "run": self._exit
            },
            "help": {
                "usage": "/help",
                "desc": "Print a menu listing all available commands.",
                "argc": 0,
                "run": self._help
            },
            "agent": {
                "usage": "/agent",
                "desc": "Toggles Agent Mode on/off for complex autonomous research.",
                "argc": 0,
                "run": self._toggle_agent
            }
        }


    def _select_item_from_id_dict(self, id_dicts: list[dict[str, str]]) -> Any:
        labels = [item["label"] for item in id_dicts]
        label_to_id = {item["label"]: item["id"] for item in id_dicts}
        return label_to_id[self._ui.select_item(labels)]


    def _help(self) -> None:
        self._ui.display_help(self._COMMANDS)


    def _save_chat(self, name: str, flag: str | None = None):
        name = name.strip()
        overwrite = False

        if flag:
            if flag.strip() == "-f":
                overwrite = True
            else:
                self._console.print(
                    f"\n❓ [bold red]Unknown flag:[/bold red] [bold cyan]\"{flag}\"[/bold cyan]. "
                    "Did you mean [bold cyan]\"-f\"[/bold cyan]?"
                )
                return

        try:
            self._db.insert_chat(name, self._llm.get_history(), overwrite)
            self._console.print(f"\n💾 [bold]Chat saved as [cyan]\"{name}\"[/cyan]![/bold]")

        except sqlite3.IntegrityError:
            self._console.print(f"\n⚠️  [bold yellow]Chat [bold cyan]\"{name}\"[/bold cyan] already exists! No chats saved.[/bold yellow]")
            self._console.print(f"Use [bold cyan]/chat save {name} -f[/bold cyan] to overwrite.")


    def _load_chat(self, name: str):
        name = name.strip()
        history = self._db.get_chat(name)

        if history is None:
            self._console.print(f"\n🔍 [bold yellow]Chat [bold cyan]\"{name}\"[/bold cyan] not found. No chats loaded.[/bold yellow]")
            return

        self._llm.set_history(history)
        self._console.print(f"\n📖 [bold]Successfully loaded chat history from [cyan]\"{name}\"[/cyan]![/bold]")


    def _clear_chat(self):
        self._llm.clear_history()
        self._console.print("\n🧹 [bold]Chat history cleared![/bold]")


    def _list_chats(self) -> None:
        chat_names = self._db.get_all_chat_names()
        if chat_names is None:
            return

        self._ui.display_chat_names(chat_names)


    def _delete_chat(self, arg: str) -> None:
        arg = arg.strip()

        if arg == "-a":
            self._console.print("\n⚠️  [bold yellow]WARNING: This will permanently delete ALL saved chats.[/bold yellow]")
            confirm = self._console.input("❓ [bold]Are you sure? ([cyan]y/n[/cyan]): [/bold]")

            if confirm.strip().lower() == "y":
                success = self._db.delete_all_chats()
                if success:
                    self._console.print("\n🗑️  [bold]All saved chats have been deleted![/bold]")
            else:
                self._console.print("\n🛑 [bold]Deletion canceled.[/bold]")

        else:
            success = self._db.delete_chat(arg)
            if success:
                self._console.print(f"\n🗑️  [bold]Chat [cyan]\"{arg}\"[/cyan] deleted successfully![/bold]")
            else:
                self._console.print(f"\n🔍 [bold yellow]Chat [cyan]\"{arg}\"[/cyan] not found.[/bold yellow]")


    def _set_limit(self) -> None:
        selected_limit = self._select_item_from_id_dict(CHAT_LIMITS)
        self._llm.set_chat_limit(selected_limit)
        self._console.print(f"\n📏 [bold]Chat Context Limit:[/bold] {selected_limit}")


    def _format_time(self, start_time: float, end_time: float) -> str:
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time * 1000) % 1000)
        return f"[cyan]{minutes:02d}m {seconds:02d}s {milliseconds:03d}ms[/cyan]"


    def _get_pdf_filepaths(self, filepath: Path) -> list[Path]:
        if filepath.is_file() and filepath.suffix.lower() == ".pdf":
            return [filepath]
        elif filepath.is_dir():
            return list(filepath.rglob("*.pdf"))

        self._console.print(f"\n📂 [bold yellow]No PDF files found at: [cyan]\"{filepath}\"[/cyan][/bold yellow]")
        return []


    def _get_filepath(self, filepath: str) -> Path | None:
        try:
            filepath = Path(filepath).expanduser().resolve()
        except Exception as e:
            self._console.print(f"\n🚫 [bold red]OS Error resolving path [cyan]\"{filepath}\"[/cyan]:[/bold red] {e}")
            return None

        if not filepath.exists():
            self._console.print(f"\n🚫 [bold red]Path not found: [cyan]\"{filepath}\"[/cyan][/bold red]")
            return None

        return filepath


    def _compare_min_hashes(self, sig_bytes: bytes, lsh_cands: list[tuple[int, bytes]]) -> bool:
        for cand_pid, cand_sig_bytes in lsh_cands:
            jaccard_estimate = self._minhasher.estimate_jaccard(sig_bytes, cand_sig_bytes)
            if jaccard_estimate >= JACCARD_CUTOFF:
                self._console.print(
                    f"🛑 [bold yellow]Duplicate content detected ([cyan]ID: {cand_pid}[/cyan], "
                    f"[cyan]Similarity: {jaccard_estimate:.3f}[/cyan]). Skipping.[/bold yellow]"
                )
                return True

        return False


    def _process_pdf(self, pdf_path: Path) -> int | None:
        parsed_doc = self._parser(pdf_path)

        if not parsed_doc.full_raw_text:
            self._console.print("⚠️ [yellow]Could not extract valid text. Skipping.[/yellow]")
            return

        if parsed_doc.doi or parsed_doc.arxiv or parsed_doc.pmcid or parsed_doc.pmid:
            exists = self._db.metadata_exists(parsed_doc)
            if exists is None:
                return

            if exists:
                id_str = get_active_ids(parsed_doc)
                self._console.print(f"🛑 [bold yellow]Duplicate metadata detected ([cyan]{id_str}[/cyan]). Skipping.[/bold yellow]")
                return

        sig_bytes, band_hashes = self._minhasher.minhash_doc(parsed_doc.full_raw_text)
        if sig_bytes is None or band_hashes is None:
            self._console.print("⚠️ [yellow]Document too short to fingerprint. Skipping.[/yellow]")
            return

        lsh_cands = self._db.get_lsh_candidates(band_hashes)
        if lsh_cands is None:
            return

        is_duplicate = self._compare_min_hashes(sig_bytes, lsh_cands)
        if is_duplicate:
            return

        pid = self._db.insert_paper(parsed_doc, sig_bytes, band_hashes)

        if pid == -1:
            return

        self._console.print("🧠 [bold]Generating semantic chunks and embeddings[/bold]")
        chunks = self._chunker(parsed_doc.blocks_reg)
        self._console.print(f"✅ [bold]Successfully generated [cyan]{len(chunks)}[/cyan] chunks[/bold]")
        self._db.insert_paper_chunks(chunks, pid)

        return pid

    def _load_pdfs(self, filepath: str):
        filepath = self._get_filepath(filepath)
        if filepath is None:
            return

        pdf_files = self._get_pdf_filepaths(filepath)
        if not pdf_files:
            return

        self._console.print(f"\n🚀 [bold]Starting Axon Ingestion Pipeline ([cyan]{len(pdf_files)} PDF files[/cyan])[/bold]")
        for pdf_path in pdf_files:
            self._console.print()
            self._console.rule(f"[bold cyan]{pdf_path.name}[/bold cyan]", style="bold")

            start_time = time.perf_counter()
            pid = self._process_pdf(pdf_path)
            if pid is None:
                continue

            end_time = time.perf_counter()
            time_str = self._format_time(start_time, end_time)
            self._console.print(f"✅ [bold]Paper ingested successfully ([cyan]ID: {pid}[/cyan]) in {time_str}.[/bold]")


    def _clear_db(self):
        self._console.print("\n⚠️  [bold yellow]WARNING: This will permanently delete ALL papers, chunks, embeddings, and saved chats.[/bold yellow]")
        confirm = self._console.input("❓ [bold]Are you sure? ([cyan]y/n[/cyan]): [/bold]").strip().lower()
        if confirm == 'y':
            self._db.reset()
            self._console.print("\n💥 [bold]Vector database completely cleared![/bold]")
        else:
            self._console.print("\n🛑 [bold]Database clear canceled.[/bold]")


    def _clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")


    def _exit(self):
        self._console.print("\n👋 [bold]Shutting down Axon. Goodbye![/bold]")
        return True


    def _compact(self):
        with self._ui.wait():
            response = self._llm.compact()

        if response is not None:
            self._ui.stream_response(response)
            self._console.print(f"\n📦 [bold]Successfully compacted chat history![/bold]")


    def _toggle_agent(self):
        self._agent_mode_enabled = not self._agent_mode_enabled
        status = "on" if self._agent_mode_enabled else "off"
        self._console.print(f"\n🧠 [bold]Agent Mode successfully toggled [cyan]{status}[/cyan]![/bold]")


    def _auto_compact(self):
        bool_val = self._llm.toggle_auto_compact()
        status = "on" if bool_val else "off"
        self._console.print(f"\n⚙️  [bold]Auto-compact successfully toggled [cyan]{status}[/cyan]![/bold]")


    def _select_model(self) -> None:
        selected_model = self._select_item_from_id_dict(LLMS)

        self._llm_adapter = create_llm_adapter(selected_model, self._console)
        self._llm.set_llm_adapter(self._llm_adapter)
        self._llm.set_chat_llm(selected_model)

        self._console.print(f"\n🤖 [bold]Using Model:[/bold] {selected_model}")


    def _chat_roll(self):
        bool_val = self._llm.toggle_chat_roll()
        status = "on" if bool_val else "off"
        self._console.print(f"\n🔄  [bold]Chat rolling successfully toggled [cyan]{status}[/cyan]![/bold]")


    def _process_cmd(self, cmd: str) -> bool:
        cmd = cmd.lstrip("/")
        parts = cmd.split()
        num_parts = len(parts)
        base = parts[0]
        sub = None if num_parts == 1 else parts[1]

        invalid_command = (
            (base not in self._COMMANDS) or
            (num_parts == 1 and "subcommands" in self._COMMANDS[base]) or
            (num_parts > 1 and "subcommands" not in self._COMMANDS[base]) or
            (
                num_parts > 1 and
                "subcommands" in self._COMMANDS[base] and
                sub not in self._COMMANDS[base]["subcommands"]
            )
        )

        if invalid_command:
            self._console.print(
                f"\n❓ [bold red]Unknown command:[/bold red] [bold cyan]\"{cmd}\"[/bold cyan]. "
                "Type [bold cyan]/help[/bold cyan] for a list of available commands."
            )
            return False

        if "subcommands" in self._COMMANDS[base]:
            cmd_data = self._COMMANDS[base]["subcommands"][sub]
            args = parts[2:]
        else:
            cmd_data = self._COMMANDS[base]
            args = parts[1:]

        cmd_args = cmd_data["argc"]
        if isinstance(cmd_args, list):
            correct_num_args = len(args) in cmd_args
        else:
            correct_num_args = len(args) == cmd_args

        if not correct_num_args:
            self._console.print(f"\n❌ [bold red]Invalid number of arguments.[/bold red] Usage: {cmd_data['usage']}")
            return False

        result = cmd_data["run"](*args)

        return result if result is not None else False


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




