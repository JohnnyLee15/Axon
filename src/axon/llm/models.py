GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
GEMINI_2_5_FLASH = "gemini-2.5-flash"
GEMINI_2_5_PRO = "gemini-2.5-pro"
GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"
GEMINI_3_FLASH_PREVIEW = "gemini-3-flash-preview"
GEMINI_3_5_FLASH = "gemini-3.5-flash"
GEMINI_3_1_PRO_PREVIEW = "gemini-3.1-pro-preview"

DEFAULT_CHAT_MODEL = GEMINI_3_5_FLASH
CHAT_UTILITY_MODEL = GEMINI_3_5_FLASH
INGESTION_MODEL = GEMINI_3_1_FLASH_LITE

MODEL_OPTIONS = [
    {"id": GEMINI_2_5_FLASH_LITE, "label": f"{GEMINI_2_5_FLASH_LITE} (cheapest | retires Oct 2026)"},
    {"id": GEMINI_3_1_FLASH_LITE, "label": f"{GEMINI_3_1_FLASH_LITE} (budget | stable)"},
    {"id": GEMINI_2_5_FLASH, "label": f"{GEMINI_2_5_FLASH} (low cost | retires Oct 2026)"},
    {"id": GEMINI_3_FLASH_PREVIEW, "label": f"{GEMINI_3_FLASH_PREVIEW} (mid cost | preview)"},
    {"id": GEMINI_3_5_FLASH, "label": f"{GEMINI_3_5_FLASH} (recommended | stable)"},
    {"id": GEMINI_2_5_PRO, "label": f"{GEMINI_2_5_PRO} (high cost | retires Oct 2026)"},
    {"id": GEMINI_3_1_PRO_PREVIEW, "label": f"{GEMINI_3_1_PRO_PREVIEW} (highest cost | preview)"},
]

GEMINI_PROVIDER = "gemini"

MODEL_TO_PROVIDER = {
    GEMINI_2_5_FLASH_LITE: GEMINI_PROVIDER,
    GEMINI_2_5_FLASH: GEMINI_PROVIDER,
    GEMINI_2_5_PRO: GEMINI_PROVIDER,
    GEMINI_3_1_FLASH_LITE: GEMINI_PROVIDER,
    GEMINI_3_FLASH_PREVIEW: GEMINI_PROVIDER,
    GEMINI_3_5_FLASH: GEMINI_PROVIDER,
    GEMINI_3_1_PRO_PREVIEW: GEMINI_PROVIDER,
}
