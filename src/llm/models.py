DEFAULT_CHAT_MODEL = "gemini-2.5-flash-lite"
REWRITE_MODEL = "gemini-2.5-flash-lite"
COMPACT_MODEL = "gemini-2.5-flash-lite"

MODEL_OPTIONS = [
    {"id": "gemini-2.5-flash-lite", "label": "gemini-2.5-flash-lite (cheapest | quality #6)"},
    {"id": "gemini-2.5-flash", "label": "gemini-2.5-flash (low cost | quality #5)"},
    {"id": "gemini-3.1-flash-lite-preview", "label": "gemini-3.1-flash-lite-preview (budget | quality #4)"},
    {"id": "gemini-3-flash-preview", "label": "gemini-3-flash-preview (mid cost | quality #3)"},
    {"id": "gemini-2.5-pro", "label": "gemini-2.5-pro (high cost | quality #2)"},
    {"id": "gemini-3.1-pro-preview", "label": "gemini-3.1-pro-preview (most expensive | quality #1)"},
]
GEMINI_PROVIDER = "gemini"
MODEL_TO_PROVIDER = {
    "gemini-2.5-flash-lite": GEMINI_PROVIDER,
    "gemini-2.5-flash": GEMINI_PROVIDER,
    "gemini-3.1-flash-lite-preview": GEMINI_PROVIDER,
    "gemini-3-flash-preview": GEMINI_PROVIDER,
    "gemini-2.5-pro": GEMINI_PROVIDER,
    "gemini-3.1-pro-preview": GEMINI_PROVIDER,
}
