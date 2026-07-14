from abc import ABC, abstractmethod
from typing import Any


class RerankerBackend(ABC):
    @abstractmethod
    def rerank(
        self,
        *,
        query: str,
        documents: list[str],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
