from typing import Any

from google import genai
from google.genai import types

from axon.llm.models import WEB_SEARCH_MODEL

from .backend import WebSearchBackend
from .contracts import WEB_SEARCH_FIELDS, WEB_SOURCE_FIELDS
from .prompts import WEB_SEARCH_SYSTEM_PROMPT


class GeminiWebSearchBackend(WebSearchBackend):
    def __init__(
        self,
        api_key: str,
        model: str = WEB_SEARCH_MODEL,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model


    def _extract_sources(
        self,
        response: types.GenerateContentResponse,
    ) -> list[dict[str, str]]:
        sources = []
        seen_urls = set()

        for candidate in response.candidates or []:
            metadata = candidate.grounding_metadata
            if metadata is None:
                continue

            for chunk in metadata.grounding_chunks or []:
                web = chunk.web
                if web is None or not web.uri:
                    continue

                if web.uri in seen_urls:
                    continue

                seen_urls.add(web.uri)
                sources.append({
                    WEB_SOURCE_FIELDS.TITLE: web.title or web.uri,
                    WEB_SOURCE_FIELDS.URL: web.uri,
                })

        return sources


    async def search(self, query: str) -> dict[str, Any]:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=WEB_SEARCH_SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True,
                ),
            ),
        )

        return {
            WEB_SEARCH_FIELDS.CONTENT: (response.text or "").strip(),
            WEB_SEARCH_FIELDS.SOURCES: self._extract_sources(response),
        }
