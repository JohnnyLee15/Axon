from typing import Any

# ------ Event types ------
USER_TEXT = "user_text"
MODEL_TEXT = "model_text"
TOOL_CALL = "tool_call"
TOOL_RESPONSE = "tool_response"

# ------ Shared keys ------
TYPE = "type"
TEXT = "text"
NAME = "name"
ARGS = "args"
RESULT = "result"


def user_message(text: str) -> dict[str, Any]:
    return {
        TYPE: USER_TEXT,
        TEXT: text,
    }


def model_message(text: str) -> dict[str, Any]:
    return {
        TYPE: MODEL_TEXT,
        TEXT: text,
    }


def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {
        TYPE: TOOL_CALL,
        NAME: name,
        ARGS: args
    }


def tool_response(name: str, result: str) -> dict[str, Any]:
    return {
        TYPE: TOOL_RESPONSE,
        NAME: name,
        RESULT: result,
    }


def text_message(text: str) -> list[dict[str, Any]]:
    return [user_message(text)]