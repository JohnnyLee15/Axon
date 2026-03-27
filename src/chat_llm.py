from config import *
from groq import Groq
import os
from transformers import AutoTokenizer

class ChatLLM:
    def __init__(self):
        self._chat_model = LLM_CHAT_MODEL
        self._rewrite_model = LLM_REWRITE_MODEL
        self._client = Groq(api_key=os.environ.get(GROQ_API_KEY))
        self._tokenizer = AutoTokenizer.from_pretrained(LLM_CHAT_MODEL)
        self._history = [
            {"role": "system", "content": AXON_SYSTEM_PROMPT}
        ]


    def get_token_count(self, history: list[dict[str, str]] | None = None) -> int:
        if history is None:
            history = self._history

        tokens = self._tokenizer.apply_chat_template(
            history,
            add_generation_prompt=True
        )
        return len(tokens)


    def rewrite_query(self, query: str) -> str:
        chat_only = self._history[1:]
        recent_turns = chat_only[-REWRITE_MESSAGES:]

        transcript = ""

        for msg in recent_turns:
            role = "User" if msg["role"] == "user" else "Assistant"
            raw_content = msg["content"]
            clean_content = raw_content.split(USER_HEADER)[-1].strip()
            transcript += f"{role}: {clean_content}\n"


        user_content = f"History:\n{transcript.strip()}\n\nNew Question:\n{query}"
        try:
            chat_completion = self._client.chat.completions.create(
                messages = [
                    {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                model = self._rewrite_model,
                temperature=LLM_REWRITE_TEMP
            )
            return chat_completion.choices[0].message.content.strip()

        except Exception:
            return query


    def query_chat(self, query: str) -> str:
        new_message = {"role": "user", "content": query}
        projected_history = self._history + [new_message]
        projected_len = self.get_token_count(projected_history)

        if projected_len > LLM_CHAT_MAX_TOKS:
            pass
            # TODO: return error message

        self._history = projected_history
        try:
            chat_completion = self._client.chat.completions.create(
                messages=self._history,
                model = self._chat_model,
                temperature=LLM_CHAT_TEMP
            )

            response_text = chat_completion.choices[0].message.content.strip()
            self._history.append({"role": "assistant", "content": response_text})
            return response_text

        except Exception as e:
            pass
            # TODO: return error message
