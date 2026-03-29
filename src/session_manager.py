from semantic_chunker import SemanticChunker
from pdf_parser import PdfParser
from vector_database import VectorDatabase
from axon_ui import AxonUI
from chat_llm import ChatLLM
from config import *
from rich.console import Console


class SessionManager:
    def __init__(self):
        self._parser = PdfParser()
        self._chunker = SemanticChunker()
        self._db = VectorDatabase()
        self._ui = AxonUI()
        self._llm = ChatLLM()
        self._console = Console()

        self._CHAT_COMMANDS = {
            "save": {
                "usage": "/chat save <file path>",
                "desc": "Saves the current chat history to disk.",
                "argc": 1,
                "run": self._save_chat
            },
            "load": {
                "usage": "/chat load <file path>",
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
            }
            #TODO: add /chat roll
        }

        self._DB_COMMANDS = {
            "load": {
                "usage": "/db load <file path>",
                "desc": "Loads a file or folder (and subfolders) of PDFs into the database.",
                "argc": 0,
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
            }
        }


    def _save_chat(self):
        pass


    def _load_chat(self):
        pass

    def _clear_chat(self):
        pass

    def _set_limit(self):
        pass

    def _load_pdfs(self):
        pass

    def _clear_db(self):
        pass

    def _clear_screen(self):
        pass

    def _exit(self):
        return True

    def _compact(self):
        pass

    def _auto_compact(self):
        pass

    def _select_model(self):
        model_labels = [model["label"] for model in LLMS]
        label_to_id = {model["label"]: model["id"] for model in LLMS}
        selected_model = label_to_id[self._ui.select_item(model_labels)]
        self._llm.set_chat_llm(selected_model)
        self._console.print(f"\n🤖 [bold]Using Model:[/bold] {selected_model}")

    # def _chat_roll(self):
    #     pass

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
                f"\nUnknown command: '{cmd}'. "
                "Type [bold cyan]/help[/bold cyan] for a list of available commands."
            )
            return False

        if "subcommands" in self._COMMANDS[base]:
            cmd_data = self._COMMANDS[base]["subcommands"][sub]
            args = parts[2:]
        else:
            cmd_data = self._COMMANDS[base]
            args = parts[1:]

        if len(args) != cmd_data["argc"]:
            self._console.print(f"\nInvalid number of arguments. Usage: {cmd_data['usage']}")
            return False

        return cmd_data["run"](*args)


    def run(self) -> None:
        done = False
        while not done:
            curr_tokens = self._llm.get_token_count()
            user_input = self._ui.listen(curr_tokens)
            if not user_input:
                continue

            if user_input.startswith("/"):
                done = self._process_cmd(user_input)
                continue

            with self._ui.wait():
                search_query = self._llm.rewrite_query(user_input)
                embedding = self._chunker.embed_query(search_query)
                chunks = self._db.get_formatted_chunks(embedding)
                response = self._llm.query_chat(user_input, chunks)

            self._ui.stream_response(response)



