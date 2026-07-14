from .models import Chunk

class ChunkTracker:
    def __init__(self) -> None:
        self._chunks = {}
        self._curr_chunk = ""
        self._curr_id = 0
        self._last_was_header = False


    def __len__(self) -> int:
        return len(self._curr_chunk)


    def add_text(self, next_text: str, is_header: bool = False) -> None:
        if not next_text:
            return

        self._curr_chunk += next_text
        self._last_was_header = is_header


    def flush(self) -> None:
        if self._curr_chunk:
            self._chunks[self._curr_id] = Chunk(
                markdown=self._curr_chunk,
                embedding=None
            )

            self._curr_chunk = ""
            self._curr_id += 1
            self._last_was_header = False


    def get_chunks(self) -> dict[int, Chunk]:
        return self._chunks


    def is_empty(self) -> bool:
        return len(self._curr_chunk) == 0


    def last_was_header(self) -> bool:
        return self._last_was_header

