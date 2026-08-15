from typing import Any

from axon.web_search.backend import WebSearchBackend
from axon.web_search.contracts import WEB_SEARCH_FIELDS, WEB_SOURCE_FIELDS
from .tool_contracts import TOOL_RESULTS


NO_WEB_RESULTS = "No web search results found."


class WebSearchTool:
    def __init__(self, backend: WebSearchBackend) -> None:
        self._backend = backend


    def _format_content(
        self,
        content: str,
        sources: list[dict[str, str]],
    ) -> str:
        if not sources:
            return content or NO_WEB_RESULTS

        parts = [content, "", "Sources:"]

        for i, source in enumerate(sources, start=1):
            title = source[WEB_SOURCE_FIELDS.TITLE]
            url = source[WEB_SOURCE_FIELDS.URL]
            parts.append(f"{i}. {title}: {url}")

        return "\n".join(parts)


    async def search_web(self, query: str) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return {
                TOOL_RESULTS.CONTENT: "No web search query provided.",
                TOOL_RESULTS.SOURCES: [],
            }

        try:
            result = await self._backend.search(query)
        except Exception as e:
            return {
                TOOL_RESULTS.CONTENT: f"Web search failed: {e}.",
                TOOL_RESULTS.SOURCES: [],
            }

        content = result[WEB_SEARCH_FIELDS.CONTENT]
        sources = result[WEB_SEARCH_FIELDS.SOURCES]

        return {
            TOOL_RESULTS.CONTENT: self._format_content(content, sources),
            TOOL_RESULTS.SOURCES: sources,
        }
