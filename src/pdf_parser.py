import os
import json
import logging

# Suppress logging
logging.disable(logging.INFO)

from groq import Groq
from docling.datamodel.base_models import DocItemLabel
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
from docling_core.types.doc import DoclingDocument, NodeItem, TableItem
from config import *
from block_tracker import BlockTracker, Block
from rich.console import Console
import time

console = Console()

class PdfParser:
    """
    Parses PDF research papers into structured text blocks by applying
    rule-based and LLM filtering to remove academic noise.
    """

    def __init__(self) -> None:
        self.model = LLM_CURATION_MODEL
        self.client = Groq(api_key=os.environ.get(GROQ_API_KEY))

        # TODO: Implement universal device detection (CUDA, MPS, XPU)
        device = AcceleratorDevice.MPS

        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.accelerator_options = AcceleratorOptions(device=device)

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )

    def __call__(self, filepath: str) -> dict[int, Block]:
        """
        Converts a PDF to structured blocks, filters duplicates, and removes academic noise.
        """

        console.print(
            f"[bold]🚀 Starting PDF extraction for:[/bold] {os.path.basename(filepath)}"
        )

        start_time = time.perf_counter()
        doc = self.converter.convert(filepath).document
        item_iter = iter(doc.iterate_items())
        tracker = BlockTracker()
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

        blocks_reg = tracker.get_blocks_reg()
        console.print(
            f"[bold]✨ Initial extraction complete:[/bold] Found {len(blocks_reg)} potential blocks"
        )

        blocks_reg = self._remove_noise_blocks(blocks_reg)

        end_time = time.perf_counter()
        time_formatted = self._format_time(start_time, end_time)

        console.print(
            f"[bold]🎉 PDF extraction complete in {time_formatted}! "
            f"Returning {len(blocks_reg)} clean blocks.[/bold]"
        )
        return blocks_reg


    def _is_potentially_noise(self, text: str) -> bool:
        """
        Applies rule-based checks to flag likely academic noise.
        """

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
        """
        Extracts raw text and applies Markdown formatting based on the layout label.
        """

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
        """
        Routes the document item to the correct extraction method based on its type.
        """

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
        tracker: BlockTracker
    ):
        """
        Processes a single item, adding a block to the Tracker if it passes validity checks.
        """

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

        tracker.add_block(markdown, item.label.name, self._is_potentially_noise(markdown))


    def _get_noise_blocks(self, batch_text: str) -> list[int]:
        """
        Calls the LLM to identify noisy blocks and returns their integer IDs.
        """

        formatted_prompt = f"### INPUT DATA:\n{batch_text}"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": LLM_CURATION_PROMPT},
                    {"role": "user", "content": formatted_prompt}
                ],
                model=self.model,
                temperature=LLM_CURATION_MODEL_TEMPERATURE,
                tools=[CURATION_TOOL],
                tool_choice={"type": "function", "function": {"name": "submit_noise_blocks"}}
            )

            tool_call = chat_completion.choices[0].message.tool_calls[0]
            raw_args = tool_call.function.arguments
            console.print("[bold]✅ Curation LLM responded successfully with tool arguments.[/bold]")

            parsed_args = json.loads(raw_args)
            return parsed_args.get("noise_block_ids", [])

        except Exception as e:
            # Return empty list to prevent pipeline crashes on API timeouts or malformed JSON
            console.print(f"[bold]❌ Curation LLM API Error:[/bold] {e}")
            return []

    def _remove_noise_blocks(self, blocks_reg: dict) -> dict:
        """
        Batches flagged blocks to the LLM for evaluation and filters out confirmed noise.
        """

        noise_risk_bids = [b for b in blocks_reg if blocks_reg[b].is_noise_risk]
        if not noise_risk_bids:
            console.print(
                "[bold]✨ No noise risks flagged by rule-based checks. Skipping LLM Curation [/bold]"
            )
            return blocks_reg

        console.print(f"[bold]🤖 LLM Curation:[/bold] Evaluating {len(noise_risk_bids)} high-risk noise blocks")

        current_batch_text = ""
        bids_to_remove = []
        current_batch_count = 0
        for bid in noise_risk_bids:
            block_text = blocks_reg[bid].markdown
            entry = f"\n=============\n[BID: {bid}]\n{block_text}\n"

            if len(current_batch_text) + len(entry) > LLM_CURATION_BATCH_CHAR_LIMIT:
                console.print(f"    📤 Sending batch of {current_batch_count} blocks to LLM")
                bids_to_remove.extend(self._get_noise_blocks(current_batch_text))
                current_batch_text = ""
                current_batch_count = 0

            current_batch_text += entry
            current_batch_count += 1

        # Catch the final, partially-filled batch
        if current_batch_text:
            console.print(f"    📤 Sending final batch of {current_batch_count} blocks to LLM")
            bids_to_remove.extend(self._get_noise_blocks(current_batch_text))

        console.print(f"[bold]✅ Curation Finished: Removed {len(bids_to_remove)} noise blocks total[/bold]")
        return {b: blocks_reg[b] for b in blocks_reg if b not in bids_to_remove}

    def _format_time(self, start_time: float, end_time: float) -> str:
        """
        Calculates the elapsed execution time and formats.
        """
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time * 1000) % 1000)
        return f"[cyan]{minutes:02d}m {seconds:02d}s {milliseconds:03d}ms[/cyan]"

