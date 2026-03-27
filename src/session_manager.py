from semantic_chunker import SemanticChunker
from pdf_parser import PdfParser
from vector_database import VectorDatabase
from axon_ui import AxonUI
from chat_llm import ChatLLM
from config import *

class SessionManager:
    def __init__(self):
        self._parser = PdfParser()
        self._chunker = SemanticChunker()
        self._db = VectorDatabase()
        self._ui = AxonUI()
        self._llm = ChatLLM()


    def _process_cmd(self, cmd: str) -> None:
        return True

    def _construct_query(self, chunks: str | None, user_input: str) -> str:
        chunks_text = chunks if chunks else NO_CHUNKS_TEXT
        return f"""# Retrieved Excerpts
{chunks_text}

# User Question:
{user_input}
""".strip()


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
                query = self._construct_query(chunks, user_input)
                response = self._llm.query_chat(query)

            self._ui.stream_response(response)



