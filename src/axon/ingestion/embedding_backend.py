from abc import ABC, abstractmethod

from .models import Chunk


class EmbeddingBackend(ABC):
    @abstractmethod
    def embed_chunks(self, chunks: dict[int, Chunk]) -> None:
        raise NotImplementedError


    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError
