class LLMContract:
    # Event types
    USER_TEXT = "user_text"
    MODEL_TEXT = "model_text"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"

    # Shared keys
    TYPE = "type"
    TEXT = "text"
    NAME = "name"
    ARGS = "args"
    RESULT = "result"

    # Generation response keys
    TOOL_CALLS = "tool_calls"
    RAW = "raw"

LLM_CONTRACT = LLMContract()