from pathlib import Path
import re

from src.llm.history import text_message
from src.llm.llm_adapter import LLMAdapter
from src.llm.models import INGESTION_MODEL
from src.ui.axon_ui import AxonUI

from .models import ParsedDocument
from .prompts import TITLE_EXTRACTION_SCHEMA, TITLE_EXTRACTION_PROMPT


IDENTIFIER_GROUP = "identifier"

DOI_TEXT_PATTERN = re.compile(r"\b(?P<identifier>10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")
PMCID_TEXT_PATTERN = re.compile(r"\b(?P<identifier>PMC\d+)\b", re.IGNORECASE)
PMCID_FILENAME_PATTERN = re.compile(r"^(?P<identifier>PMC\d+)$", re.IGNORECASE)
PMID_TEXT_PATTERN = re.compile(r"\bpmid\s*:?\s*(?P<identifier>\d+)\b", re.IGNORECASE)
ARXIV_FILENAME_PATTERN = re.compile(r"^(?P<identifier>\d{4}\.\d{4,5}(?:v\d+)?)$", re.IGNORECASE)
ARXIV_TEXT_PATTERN = re.compile(
    r"\barxiv:\s*(?P<identifier>"
    r"(?:\d{4}\.\d{4,5}|[A-Za-z\-]+(?:\.[A-Za-z\-]+)?/\d{7})"
    r"(?:v\d+)?"
    r")\b",
    re.IGNORECASE,
)
DOI_TRAILING_PUNCTUATION = ".,;:"

TITLE_EXTRACTION_TEMPERATURE = 0.0


class MetadataExtractor:
    def __init__(self, ui: AxonUI, llm_adapter: LLMAdapter) -> None:
        self._model = INGESTION_MODEL
        self._ui = ui
        self._llm_adapter = llm_adapter


    def _find_identifier(self, pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        if match is None:
            return None

        return match.group(IDENTIFIER_GROUP)


    def _extract_identifiers(self, parsed_doc: ParsedDocument, filename: str) -> None:
        flat_text = parsed_doc.page_one.replace("\n", " ").strip()

        doi = self._find_identifier(DOI_TEXT_PATTERN, flat_text)
        if doi:
            parsed_doc.doi = doi.rstrip(DOI_TRAILING_PUNCTUATION)

        pmcid = (
            self._find_identifier(PMCID_TEXT_PATTERN, flat_text) or
            self._find_identifier(PMCID_FILENAME_PATTERN, filename)
        )
        if pmcid:
            parsed_doc.pmcid = pmcid.upper()

        parsed_doc.arxiv = (
            self._find_identifier(ARXIV_TEXT_PATTERN, flat_text) or
            self._find_identifier(ARXIV_FILENAME_PATTERN, filename)
        )

        parsed_doc.pmid = self._find_identifier(PMID_TEXT_PATTERN, flat_text)


    def _extract_title_with_llm(self, document_page_one: str) -> str | None:
        if not document_page_one:
            return

        try:
            self._ui.progress("Triggering LLM Title Extractor Fallback.")
            prompt = f"<first_page_text>\n{document_page_one}\n</first_page_text>"

            parsed_args = self._llm_adapter.generate_json(
                model=self._model,
                contents=text_message(prompt),
                system_instruction=TITLE_EXTRACTION_PROMPT,
                schema=TITLE_EXTRACTION_SCHEMA,
                temperature=TITLE_EXTRACTION_TEMPERATURE,
            )

            title = parsed_args.get("title")
            if not isinstance(title, str):
                return None

            title = " ".join(title.strip().lstrip("#").split())
            if not title or title.lower() == "null":
                return None

            self._ui.success("Document title extracted successfully.")
            return title

        except Exception as e:
            self._ui.error(f"LLM title extraction failed: {e}.")

        return None


    def extract(self, parsed_doc: ParsedDocument, filepath: Path) -> None:
        self._extract_identifiers(parsed_doc, filepath.stem)
        if parsed_doc.title:
            return

        parsed_doc.title = self._extract_title_with_llm(parsed_doc.page_one.strip())

        if not parsed_doc.title:
            filename_title = filepath.stem.replace("-", " ").replace("_", " ")
            parsed_doc.title = " ".join(filename_title.split())
