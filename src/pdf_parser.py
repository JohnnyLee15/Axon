import os
import json
import logging

# Suppress logging
logging.disable(logging.INFO)

from google import genai
from docling.datamodel.base_models import DocItemLabel
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
from docling_core.types.doc import DoclingDocument, NodeItem, TableItem
from config import *
from document_state import DocumentState, Block
from rich.console import Console
import time

class PdfParser:
    """
    Parses PDF research papers into structured text blocks by applying
    rule-based and LLM filtering to remove academic noise.
    """

    def __init__(self, console: Console) -> None:
        self._model = LLM_CURATION_MODEL
        self._client = genai.Client(api_key=os.environ.get(GEM_API_KEY))

        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        device = AcceleratorDevice.MPS

        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.accelerator_options = AcceleratorOptions(device=device)

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )
        self._console = console

    def __call__(self, filepath: str) -> dict[str, str | dict[int, Block]]:
        self._console.print(
            f"[bold]🚀 Starting PDF extraction for:[/bold] {os.path.basename(filepath)}"
        )

        start_time = time.perf_counter()
        doc = self._converter.convert(filepath).document
        item_iter = iter(doc.iterate_items())
        tracker = DocumentState()
        processing = True

        while processing:
            curr = next(item_iter, None)
            if curr is None:
                processing = False
                continue

            item, level = curr
            is_reference_header = (
                item.label.name == "SECTION_HEADER" and
                item.text and
                item.text.strip().lower() in REFERENCE_HEADERS
            )

            if is_reference_header:
                processing = False
                continue

            self._extract_block(doc, item, level, tracker)

        blocks_reg, full_text, page1, title = tracker.get_doc_state()
        title, doi = self._extract_metadata(page1, title)

        self._console.print(
            f"[bold]✨ Initial extraction complete:[/bold] Found {len(blocks_reg)} potential blocks"
        )

        blocks_reg = self._remove_noise_blocks(blocks_reg)

        end_time = time.perf_counter()
        time_formatted = self._format_time(start_time, end_time)

        self._console.print(
            f"[bold]🎉 PDF extraction complete in {time_formatted}! "
            f"Returning {len(blocks_reg)} clean blocks.[/bold]"
        )

        return {
            "blocks_reg": blocks_reg,
            "title": title,
            "doi": doi,
            "full_text": full_text
        }


    def _extract_metadata(self, page1: str, title: str | None) -> tuple[str | None, str | None]:
        doi = None

        flat_text = page1.replace("\n", " ").strip()
        doi_match = DOI_PATTERN.search(flat_text)
        if doi_match:
            doi = doi_match.group(0).strip(".,;")

        if not title or not doi:
            try:
                self._console.print("[bold]🤖 Triggering LLM Metadata Fallback[/bold]")
                prompt = f"<first_page_text>\n{page1}\n</first_page_text>"

                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config={
                        "system_instruction": DOI_TITLE_PROMPT,
                        "temperature": LLM_METADATA_MODEL_TEMPERATURE,
                        "response_mime_type": "application/json",
                        "response_schema": DOI_TITLE_SCHEMA
                    }
                )

                self._console.print("[bold]✅ Curation LLM responded successfully with tool arguments[/bold]")
                parsed_args = json.loads(response.text)

                if not title:
                    llm_title = parsed_args.get("title")
                    if llm_title:
                        title = llm_title.lstrip("#").strip().lower()

                if not doi:
                    doi = parsed_args.get("doi")

            except Exception as e:
                self._console.print(f"[bold red]❌ LLM Metadata Fallback Error:[/bold red] {e}")

        return title, doi


    def _is_potentially_noise(self, text: str) -> bool:
        text_lower = text.strip().lower()

        # Strip markdown formatting
        clean_text = text_lower.replace('#', '').strip()
        if clean_text in SCIENTIFIC_HEADERS:
            return False

        for pattern in NOISE_REGEX_PATTERNS:
            if pattern.search(text_lower):
                return True

        words = text_lower.split()
        if len(words) <= MIN_WORD_COUNT_THRESHOLD:
            return True

        return False

    def _extract_item_with_text_attr(self, item: NodeItem, level: int) -> str:
        if not item.text:
            return ""
        text = item.text.strip()

        # Fix hyphenation across lines
        text = HYPHEN_WRAP_PATTERN.sub(r'\1\2', text)

        # Apply markdown formatting based on the label
        if item.label == DocItemLabel.SECTION_HEADER:
            return f"{'#' * max(1, level)} {text}"
        elif item.label == DocItemLabel.LIST_ITEM:
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
            return self._extract_item_with_text_attr(item, level)

        return ""


    def _extract_block(
        self,
        doc: DoclingDocument,
        item: NodeItem,
        level: int,
        tracker: DocumentState
    ):
        if item.label in EXCLUDED_DOCLING_LABELS:
            return None

        is_tiny_text = (
            item.label.name == "TEXT" and
            item.text and
            len(item.text) <= MIN_CHAR_COUNT
        )
        if is_tiny_text:
            return None

        markdown = self._extract_block_text(doc, item, level)

        # Ensure text contains numbers or letters
        if not any(char.isalnum() for char in markdown):
            return None


        # Get page number of item from first prov only
        page_no = item.prov[0].page_no if hasattr(item, "prov") and item.prov else None

        tracker.add_block(markdown, item.label.name, page_no, self._is_potentially_noise(markdown))


    def _get_noise_blocks(self, batch_text: str) -> list[int]:
        formatted_prompt = f"<input_blocks>\n{batch_text}\n</input_blocks>"

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=formatted_prompt,
                config={
                    "system_instruction": LLM_CURATION_PROMPT,
                    "temperature": LLM_CURATION_MODEL_TEMPERATURE,
                    "response_mime_type": "application/json",
                    "response_schema": CURATION_TOOL
                }
            )

            self._console.print("[bold]✅ Curation LLM responded successfully with tool arguments[/bold]")
            parsed_args = json.loads(response.text)
            return parsed_args.get("noise_block_ids", [])

        except Exception as e:
            # Return empty list to prevent pipeline crashes on API timeouts or malformed JSON
            self._console.print(f"[bold red]❌ Curation LLM API Error: {e}[/bold red]")
            return []

    def _remove_noise_blocks(self, blocks_reg: dict) -> dict:
        noise_risk_bids = [b for b in blocks_reg if blocks_reg[b].is_noise_risk]
        if not noise_risk_bids:
            self._console.print(
                "[bold]✨ No noise risks flagged by rule-based checks. Skipping LLM Curation [/bold]"
            )
            return blocks_reg

        self._console.print(f"[bold]🤖 LLM Curation:[/bold] Evaluating {len(noise_risk_bids)} high-risk noise blocks")

        current_batch_text = ""
        bids_to_remove = []
        current_batch_count = 0
        for bid in noise_risk_bids:
            block_text = blocks_reg[bid].markdown
            entry = f"<block id='{bid}'>\n{block_text}\n</block>\n"

            if len(current_batch_text) + len(entry) > LLM_CURATION_BATCH_CHAR_LIMIT:
                self._console.print(f"    📤 Sending batch of {current_batch_count} blocks to LLM")
                bids_to_remove.extend(self._get_noise_blocks(current_batch_text))
                current_batch_text = ""
                current_batch_count = 0

            current_batch_text += entry
            current_batch_count += 1

        # Catch the final, partially-filled batch
        if current_batch_text:
            self._console.print(f"    📤 Sending final batch of {current_batch_count} blocks to LLM")
            bids_to_remove.extend(self._get_noise_blocks(current_batch_text))

        self._console.print(f"[bold]✅ Curation Finished: Removed {len(bids_to_remove)} noise blocks total[/bold]")
        return {b: blocks_reg[b] for b in blocks_reg if b not in bids_to_remove}

    def _format_time(self, start_time: float, end_time: float) -> str:
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time * 1000) % 1000)
        return f"[cyan]{minutes:02d}m {seconds:02d}s {milliseconds:03d}ms[/cyan]"

