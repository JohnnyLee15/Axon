import unittest
from unittest.mock import AsyncMock, Mock

from axon.web_search.contracts import WEB_SEARCH_FIELDS
from axon.web_search.gemini_backend import GeminiWebSearchBackend


class GeminiWebSearchBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_disables_automatic_function_calling(self) -> None:
        backend = object.__new__(GeminiWebSearchBackend)
        backend._client = Mock()
        backend._client.aio.models.generate_content = AsyncMock(
            return_value=Mock(text="grounded result", candidates=[]),
        )
        backend._model = "gemini-test"

        result = await backend.search("current information")

        config = (
            backend._client.aio.models.generate_content.await_args.kwargs["config"]
        )
        self.assertIsNotNone(config.automatic_function_calling)
        self.assertTrue(config.automatic_function_calling.disable)
        self.assertEqual(result[WEB_SEARCH_FIELDS.CONTENT], "grounded result")


if __name__ == "__main__":
    unittest.main()
