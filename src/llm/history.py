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


def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {
        LLM_CONTRACT.TYPE: LLM_CONTRACT.TOOL_CALL,
        LLM_CONTRACT.NAME: name,
        LLM_CONTRACT.ARGS: args
    }


def tool_response(name: str, result: str) -> dict[str, Any]:
    return {
        LLM_CONTRACT.TYPE: LLM_CONTRACT.TOOL_RESPONSE,
        LLM_CONTRACT.NAME: name,
        LLM_CONTRACT.RESULT: result,
    }


def text_message(text: str) -> list[dict[str, Any]]:
    return [user_message(text)]