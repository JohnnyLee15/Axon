import unittest
from unittest.mock import AsyncMock, Mock

from axon.agent.tool_contracts import TOOL_RESULTS
from axon.agent.web_search_tool import NO_WEB_RESULTS, WebSearchTool
from axon.web_search.contracts import WEB_SEARCH_FIELDS, WEB_SOURCE_FIELDS


class WebSearchToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.backend = Mock()
        self.backend.search = AsyncMock()
        self.tool = WebSearchTool(backend=self.backend)

    async def test_rejects_empty_query_without_searching(self) -> None:
        result = await self.tool.search_web("   ")

        self.backend.search.assert_not_awaited()
        self.assertEqual(result[TOOL_RESULTS.CONTENT], "No web search query provided.")
        self.assertEqual(result[TOOL_RESULTS.SOURCES], [])

    async def test_returns_formatted_content_and_structured_sources(self) -> None:
        sources = [
            {
                WEB_SOURCE_FIELDS.TITLE: "Example",
                WEB_SOURCE_FIELDS.URL: "https://example.com",
            }
        ]
        self.backend.search.return_value = {
            WEB_SEARCH_FIELDS.CONTENT: "A grounded summary.",
            WEB_SEARCH_FIELDS.SOURCES: sources,
        }

        result = await self.tool.search_web("  current example  ")

        self.backend.search.assert_awaited_once_with("current example")
        self.assertEqual(result[TOOL_RESULTS.SOURCES], sources)
        self.assertEqual(
            result[TOOL_RESULTS.CONTENT],
            "A grounded summary.\n\nSources:\n1. Example: https://example.com",
        )

    async def test_returns_fallback_when_search_has_no_results(self) -> None:
        self.backend.search.return_value = {
            WEB_SEARCH_FIELDS.CONTENT: "",
            WEB_SEARCH_FIELDS.SOURCES: [],
        }

        result = await self.tool.search_web("missing topic")

        self.assertEqual(result[TOOL_RESULTS.CONTENT], NO_WEB_RESULTS)
        self.assertEqual(result[TOOL_RESULTS.SOURCES], [])

    async def test_converts_backend_error_to_tool_result(self) -> None:
        self.backend.search.side_effect = RuntimeError("unavailable")

        result = await self.tool.search_web("current news")

        self.assertEqual(
            result[TOOL_RESULTS.CONTENT],
            "Web search failed: unavailable.",
        )
        self.assertEqual(result[TOOL_RESULTS.SOURCES], [])


if __name__ == "__main__":
    unittest.main()
