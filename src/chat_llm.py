from config import *
import os
from google import genai

class ChatLLM:
    def __init__(self):
        self._chat_model = LLM_CHAT_MODEL_DEFAULT
        self._context_size = LLM_CONTEXT_SIZE_DEFAULT
        self._rewrite_model = LLM_REWRITE_MODEL
        self._client = genai.Client(api_key=os.environ.get(GEM_API_KEY))
        self._history = []


    def set_chat_llm(self, model: str) -> None:
        self._chat_model = model


    def set_chat_limit(self, limit: int) -> None:
        self._context_size = limit


    def get_chat_limit(self) -> int:
        return self._context_size


    def clear_history(self) -> None:
        self._history = []


    def get_history(self) -> list[dict[str, str]]:
        return self._history


    def set_history(self, history: list[dict[str, str]]) -> None:
        self._history = history


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
        #TODO: Add check to ensure returned query is <-8000 chars
        #TODO: Change rewriter to attempt rewrite if needed
        recent_turns = self._history[-REWRITE_MESSAGES:]

        transcript = ""
        for msg in recent_turns:
            role = "User" if msg["role"] == "user" else "Model"
            content = msg["parts"][0]["text"]
            transcript += f"{role}: {content}\n"

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


    def _construct_query(self, chunks: str | None, user_input: str) -> str:
        if not chunks:
            return user_input

        return f"Retrieved Excerpts:\n{chunks}\n\nUser Question:\n{user_input}".strip()


    def _add_history(self, user_input: str, response: str) -> None:
        self._history.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })
        self._history.append({
            "role": "model",
            "parts": [{"text": response}]
        })


    def query_chat(self, user_input: str, chunks: str | None) -> str:
        new_message = {
            "role": "user",
            "parts": [{"text": self._construct_query(chunks, user_input)}]
        }

        payload= self._history + [new_message]
        payload_len = self.get_token_count(payload)

        if payload_len > self._context_size:
            pass
            # TODO: return error message

        try:
            response = self._client.models.generate_content(
                model=self._chat_model,
                contents=payload,
                config={
                    "system_instruction": AXON_SYSTEM_PROMPT,
                    "temperature": LLM_CHAT_TEMP
                }
            )

            response_text = response.text.strip()
            self._add_history(user_input, response_text)
            return response_text

        except Exception as e:
            pass
            # TODO: return error message


