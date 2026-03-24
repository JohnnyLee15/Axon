from semantic_chunker import SemanticChunker
from pdf_parser import PdfParser
from vector_database import VectorDatabase
from axon_ui import AxonUI

class SessionManager:
    def __init__(self):
        self._parser = PdfParser()
        self._chunker = SemanticChunker()
        self._db = VectorDatabase()
        self._ui = AxonUI()
        # self._llm = ChatLLM()


    def _process_cmd(self, cmd: str) -> None:
        pass


    def run(self) -> None:
        done = False
        while not done:
            user_input = self._ui.listen()
            if not user_input:
                continue

            if user_input == "/exit":
                done = True
                continue

            if user_input.startswith("/"):
                done = self._process_cmd(user_input)
                continue

            # self._llm.query(user_input)

