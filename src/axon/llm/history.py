from typing import Any

from .contracts import LLM_CONTRACT

def user_message(text: str) -> dict[str, Any]:
    return {
        LLM_CONTRACT.TYPE: LLM_CONTRACT.USER_TEXT,
        LLM_CONTRACT.TEXT: text,
    }


def model_message(text: str) -> dict[str, Any]:
    return {
        LLM_CONTRACT.TYPE: LLM_CONTRACT.MODEL_TEXT,
        LLM_CONTRACT.TEXT: text,
    }


def tool_call(
    name: str,
    args: dict[str, Any],
    provider_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        LLM_CONTRACT.TYPE: LLM_CONTRACT.TOOL_CALL,
        LLM_CONTRACT.NAME: name,
        LLM_CONTRACT.ARGS: args
    }
    if provider_metadata:
        item[LLM_CONTRACT.PROVIDER_METADATA] = provider_metadata

    return item


def tool_response(
    name: str,
    result: str,
    provider_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        LLM_CONTRACT.TYPE: LLM_CONTRACT.TOOL_RESPONSE,
        LLM_CONTRACT.NAME: name,
        LLM_CONTRACT.RESULT: result,
    }
    if provider_metadata:
        item[LLM_CONTRACT.PROVIDER_METADATA] = provider_metadata

    return item


def text_message(text: str) -> list[dict[str, Any]]:
    return [user_message(text)]


def _stringify_history_item(item: dict[str, Any]) -> str:
    item_type = item[LLM_CONTRACT.TYPE]

    if item_type == LLM_CONTRACT.USER_TEXT:
        return f"User: {item[LLM_CONTRACT.TEXT]}"

    if item_type == LLM_CONTRACT.MODEL_TEXT:
        return f"Model: {item[LLM_CONTRACT.TEXT]}"

    if item_type == LLM_CONTRACT.TOOL_CALL:
        return f"Model: called {item[LLM_CONTRACT.NAME]} with args {item[LLM_CONTRACT.ARGS]}"

    if item_type == LLM_CONTRACT.TOOL_RESPONSE:
        return f"User: tool {item[LLM_CONTRACT.NAME]} returned {item[LLM_CONTRACT.RESULT]}"

    raise ValueError(f"Unknown history item type: {item_type}")


def format_history_transcript(history: list[dict[str, Any]]) -> str:
    return "\n".join(
        _stringify_history_item(item)
        for item in history
    )
