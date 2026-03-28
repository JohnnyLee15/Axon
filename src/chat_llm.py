from config import *
import os
from google import genai

class ChatLLM:
    def __init__(self):
        self._chat_model = LLM_CHAT_MODEL
        self._rewrite_model = LLM_REWRITE_MODEL
        self._client = genai.Client(api_key=os.environ.get(GEM_API_KEY))
        self._history = []


    def get_token_count(self, history: list[dict[str, str]] | None = None) -> int:
        if history is None:
            history = self._history

        try:
            contents = [{
                "role": "user",
                "parts": [{"text": f"SYSTEM_INSTRUCTION:\n{AXON_SYSTEM_PROMPT}"}]
            }] + history
            response = self._client.models.count_tokens(model=self._chat_model, contents=contents,)
            return response.total_tokens

        except Exception as e:
            pass
            # TODO: print error

    def rewrite_query(self, query: str) -> str:
        recent_turns = self._history[-REWRITE_MESSAGES:]

        transcript = ""

        for msg in recent_turns:
            role = "User" if msg["role"] == "user" else "Model"
            raw_content = msg["parts"][0]["text"]
            clean_content = raw_content.split(USER_HEADER)[-1].strip()
            transcript += f"{role}: {clean_content}\n"

        user_content = f"History:\n{transcript.strip()}\n\nNew Question:\n{query}"
        try:
            response = self._client.models.generate_content(
                model=self._rewrite_model,
                contents=user_content,
                config={
                    "system_instruction": REWRITE_SYSTEM_PROMPT,
                    "temperature": LLM_REWRITE_TEMP
                }
            )
            return response.text.strip()

        except Exception:
            return query


    def query_chat(self, query: str) -> str:
        new_message = {
            "role": "user",
            "parts": [{"text": query}]
        }

        projected_history = self._history + [new_message]
        projected_len = self.get_token_count(projected_history)

        if projected_len > LLM_SMALL_CONTEXT_TOKS:
            pass
            # TODO: return error message

        self._history = projected_history
        try:
            response = self._client.models.generate_content(
                model=self._chat_model,
                contents=self._history,
                config={
                    "system_instruction": AXON_SYSTEM_PROMPT,
                    "temperature": LLM_CHAT_TEMP
                }
            )
            response_text = response.text.strip()

            usage = getattr(response, "usage_metadata", None)

            if usage is not None:
                prompt_tokens = getattr(usage, "prompt_token_count", None)
                cached_tokens = getattr(usage, "cached_content_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)

                print(f"Prompt tokens: {prompt_tokens}")
                print(f"Cached tokens: {cached_tokens}")
                print(f"Total tokens: {total_tokens}")

            self._history.append({
                "role": "model",
                "parts": [{"text": response_text}]
            })
            return response_text

        except Exception as e:
            pass
            # TODO: return error message
