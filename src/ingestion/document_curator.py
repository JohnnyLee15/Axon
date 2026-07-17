import re

from src.llm.models import INGESTION_MODEL
from src.ui.axon_ui import AxonUI
from src.llm.llm_adapter import LLMAdapter
from src.llm.history import text_message

from .prompts import BLOCK_CURATION_PROMPT, BLOCK_CURATION_SCHEMA, NOISE_BLOCK_IDS_KEY
from .models import Block


SCIENTIFIC_HEADERS = {
    "abstract", "introduction", "background", "objectives", "aims",
    "methods", "methodology", "materials and methods",
    "experimental procedures", "study design", "results", "findings",
    "discussion", "conclusion", "conclusions", "summary"
}

NOISE_REGEX_PATTERNS = [
    # --- URLs & Identifiers ---
    re.compile(r'https?://\S+', re.IGNORECASE),
    re.compile(r'doi:?\s*10\.', re.IGNORECASE),
    re.compile(r'orcid\.org', re.IGNORECASE),
    re.compile(r'issn\s+\d+', re.IGNORECASE),

    # --- Copyright & Licensing ---
    re.compile(r'©', re.IGNORECASE),
    re.compile(r'copyright', re.IGNORECASE),
    re.compile(r'all rights reserved', re.IGNORECASE),
    re.compile(r'open access', re.IGNORECASE),
    re.compile(r'creative commons', re.IGNORECASE),
    re.compile(r'cc\s+by(-\w+)?\b', re.IGNORECASE), # Catches CC BY, CC BY-NC, etc.

    # --- Publication History & Metadata ---
    re.compile(r'received\s+\d+', re.IGNORECASE),
    re.compile(r'revision\s+received', re.IGNORECASE),
    re.compile(r'accepted\s+\d+', re.IGNORECASE),
    re.compile(r'published\s+online', re.IGNORECASE),
    re.compile(r'available\s+online', re.IGNORECASE),
    re.compile(r'downloaded\s+from', re.IGNORECASE),

    # --- Volume/Issue/Page Formatting ---
    re.compile(r'vol(ume)?\.?\s*\d+', re.IGNORECASE),
    re.compile(r'no\.?\s*\d+', re.IGNORECASE),
    re.compile(r'pp\.?\s*\d+', re.IGNORECASE),
    re.compile(r'page\s+\d+\s+of\s+\d+', re.IGNORECASE),

    # --- Author Info & Disclaimers ---
    re.compile(r'email:', re.IGNORECASE),
    re.compile(r'correspondence:', re.IGNORECASE),
    re.compile(r'conflict(s)? of interest', re.IGNORECASE),
    re.compile(r'competing interest(s)?', re.IGNORECASE),

    # --- Document Types & Headers ---
    re.compile(r'original\s+article', re.IGNORECASE),
    re.compile(r'research\s+article', re.IGNORECASE),
    re.compile(r'keywords\.', re.IGNORECASE),
]

BLOCK_CURATION_TEMPERATURE = 0.0
MAX_SHORT_BLOCK_WORDS = 15
CURATION_BATCH_CHAR_LIMIT = 4000


class DocumentCurator:
    def __init__(self, ui: AxonUI, llm_adapter: LLMAdapter) -> None:
        self._model = INGESTION_MODEL
        self._ui = ui
        self._llm_adapter = llm_adapter


    def is_potentially_noise(self, text: str) -> bool:
        text_lower = text.strip().lower()
        clean_text = text_lower.lstrip("#").strip()

        if clean_text in SCIENTIFIC_HEADERS:
            return False

        if any(
            pattern.search(text_lower)
            for pattern in NOISE_REGEX_PATTERNS
        ):
            return True

        return len(text_lower.split()) <= MAX_SHORT_BLOCK_WORDS


    def _get_noise_block_ids(self, batch_text: str) -> list[int]:
        formatted_prompt = f"<input_blocks>\n{batch_text}\n</input_blocks>"

        try:
            response = self._llm_adapter.generate_json(
                model=self._model,
                contents=text_message(formatted_prompt),
                system_instruction=BLOCK_CURATION_PROMPT,
                schema=BLOCK_CURATION_SCHEMA,
                temperature=BLOCK_CURATION_TEMPERATURE,
            )

            return response[NOISE_BLOCK_IDS_KEY]

        except Exception as e:
            self._ui.error(f"Curation LLM API Error: {e}.")
            return []


    def curate(self, blocks_reg: dict[int, Block]) -> dict[int, Block]:
        noise_risk_bids = [b for b in blocks_reg if blocks_reg[b].is_noise_risk]
        if not noise_risk_bids:
            return blocks_reg

        self._ui.progress(f"Curating {len(noise_risk_bids)} potential noise blocks.")

        current_batch = ""
        bids_to_remove = set()

        for bid in noise_risk_bids:
            block_text = blocks_reg[bid].markdown
            entry = f"<block id='{bid}'>\n{block_text}\n</block>\n"

            if current_batch and (len(current_batch) + len(entry)) > CURATION_BATCH_CHAR_LIMIT:
                bids_to_remove.update(self._get_noise_block_ids(current_batch))
                current_batch = ""

            current_batch += entry

        if current_batch:
            bids_to_remove.update(self._get_noise_block_ids(current_batch))

        bids_to_remove.intersection_update(noise_risk_bids)

        self._ui.success(f"Removed {len(bids_to_remove)} noise blocks.")
        return {b: blocks_reg[b] for b in blocks_reg if b not in bids_to_remove}
