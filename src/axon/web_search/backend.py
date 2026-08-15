from abc import ABC, abstractmethod
from typing import Any


class WebSearchBackend(ABC):
    @abstractmethod
    async def search(self, query: str) -> dict[str, Any]:
        raise NotImplementedError
