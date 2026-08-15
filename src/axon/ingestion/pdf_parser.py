import logging
import warnings
import re
from pathlib import Path

import torch
from docling.datamodel.pipeline_options import AcceleratorDevice
from docling.datamodel.base_models import DocItemLabel, InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DoclingDocument, NodeItem, TableItem
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions
from huggingface_hub.utils import disable_progress_bars
from transformers.utils.logging import disable_progress_bar

from .document_state import DocumentState
from .models import ParsedDocument
from .metadata_extractor import MetadataExtractor
from .document_curator import DocumentCurator


MAX_TINY_TEXT_CHARS = 15
HYPHEN_WRAP_PATTERN = re.compile(r'([A-Za-z]+)-\s*\n\s*([a-z]+)')

REFERENCE_HEADERS = {
    "references",
    "bibliography",
    "literature cited",
    "works cited",
    "citations",
    "reference list",
    "selected bibliography"
}


DOCLING_LOGGER_NAMES = (
    "docling",
    "docling_core",
    "docling_parse",
    "docling_ibm_models",
    "docling-pm",
)

EXCLUDED_DOCLING_LABELS = {
    DocItemLabel.PAGE_HEADER,
    DocItemLabel.PAGE_FOOTER,
    DocItemLabel.DOCUMENT_INDEX,
    DocItemLabel.CHECKBOX_SELECTED,
    DocItemLabel.CHECKBOX_UNSELECTED,
    DocItemLabel.FORM,
    DocItemLabel.GRADING_SCALE,
    DocItemLabel.HANDWRITTEN_TEXT,
    DocItemLabel.REFERENCE,
    DocItemLabel.PICTURE
}
DOCLING_NUM_THREADS = 8


for logger_name in DOCLING_LOGGER_NAMES:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL + 1)

warnings.filterwarnings(
    "ignore",
    module=r"^(docling|docling_core|docling_parse|docling_ibm_models)(\.|$)",
)

disable_progress_bars()
disable_progress_bar()


class PdfParser:
    def __init__(
        self,
        document_curator: DocumentCurator,
        metadata_extractor: MetadataExtractor,
        artifacts_path: Path,
    ) -> None:
        self._document_curator = document_curator
        self._metadata_extractor = metadata_extractor

        pipeline_opts = PdfPipelineOptions(
            artifacts_path=artifacts_path,
            do_ocr=False,
            accelerator_options=AcceleratorOptions(
                num_threads=DOCLING_NUM_THREADS,
                device=self._get_docling_device()
            )
        )

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )


    def _get_docling_device(self) -> AcceleratorDevice:
        if torch.cuda.is_available():
            return AcceleratorDevice.CUDA
        if torch.mps.is_available():
            return AcceleratorDevice.MPS
        if torch.xpu.is_available():
            return AcceleratorDevice.XPU
        return AcceleratorDevice.CPU


    def __call__(self, filepath: Path) -> ParsedDocument:
        doc = self._converter.convert(filepath).document
        state = DocumentState()

        for item, level in doc.iterate_items():
            if self._is_reference_header(item):
                break

            self._extract_block(doc, item, level, state)

        parsed_doc = state.build()
        self._metadata_extractor.extract(parsed_doc, filepath)
        parsed_doc.blocks_reg = self._document_curator.curate(parsed_doc.blocks_reg)
        return parsed_doc


    def _is_reference_header(self, item: NodeItem) -> bool:
        return (
            item.label == DocItemLabel.SECTION_HEADER and
            item.text.strip().lower() in REFERENCE_HEADERS
        )


    def _format_item_text(self, item: NodeItem, level: int) -> str:
        if not item.text:
            return ""

        text = item.text.strip()
        text = HYPHEN_WRAP_PATTERN.sub(r'\1\2', text)
        if item.label == DocItemLabel.SECTION_HEADER:
            return f"{'#' * max(1, level)} {text}"

        if item.label == DocItemLabel.LIST_ITEM:
            return f"* {text}"

        return text

    def _extract_block_text(
        self,
        doc: DoclingDocument,
        item: NodeItem,
        level: int
    ) -> str:
        if isinstance(item, TableItem):
            return item.export_to_markdown(doc=doc).strip()

        if hasattr(item, "text"):
            return self._format_item_text(item, level)

        return ""


    def _record_document_text(
        self,
        state: DocumentState,
        item: NodeItem,
        markdown: str,
    ) -> None:
        state.add_to_full_raw_text(markdown)

        provenance = getattr(item, "prov", [])
        page_no = provenance[0].page_no if provenance else None
        if page_no != 1:
            return

        state.add_to_first_page(markdown)
        if item.label == DocItemLabel.TITLE:
            title = markdown.lstrip("#").strip()
            state.set_title_if_missing(title)


    def _should_exclude_block(
        self,
        item: NodeItem,
        markdown: str,
    ) -> bool:
        if item.label in EXCLUDED_DOCLING_LABELS:
            return True

        is_tiny_text = (
            item.label == DocItemLabel.TEXT and
            item.text and
            len(item.text) <= MAX_TINY_TEXT_CHARS
        )
        if is_tiny_text:
            return True

        return not any(char.isalnum() for char in markdown)


    def _extract_block(
        self,
        doc: DoclingDocument,
        item: NodeItem,
        level: int,
        state: DocumentState
    ) -> None:
        markdown = self._extract_block_text(doc, item, level)
        if not markdown:
            return

        self._record_document_text(state, item, markdown)

        if self._should_exclude_block(item, markdown):
            return

        state.add_block(
            markdown,
            item.label.name,
            self._document_curator.is_potentially_noise(markdown)
        )
