from types import SimpleNamespace
from typing import TypeAlias

Chunk: TypeAlias = SimpleNamespace

class ChunkTracker:
    def __init__(self) -> None:
        self._chunks = {}
        self._curr_chunk= ""
        self._curr_id = 0

    def add_text(self, next_text: str) -> None:
        if not next_text:
            return

        self._curr_chunk += next_text

    def flush(self) -> None:
        if self._curr_chunk:
            self._chunks[self._curr_id] = Chunk(
                markdown=self._curr_chunk,
                embedding=None
            )

            self._curr_chunk = ""
            self._curr_id += 1

    def len(self) -> int:
        return len(self._curr_chunk)

    def get_chunks(self) -> dict[int, Chunk]:
        return self._chunks

    def is_empty(self) -> bool:
        return len(self._curr_chunk) == 0

