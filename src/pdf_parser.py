import os
import json
from groq import Groq
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocItemLabel
from docling_core.types.doc import DoclingDocument, NodeItem
import config
from parsed_block import ParsedBlock

class PdfParser:
    """
    Parses PDF research papers into structured text blocks by applying
    rule-based and LLM filtering to remove academic noise.
    """

    def __init__(self) -> None:
        self.model: str = config.LLM_CURATION_MODEL
        self.client: Groq = Groq(api_key=os.environ.get(config.GROQ_API_KEY))
        self.converter: DocumentConverter = DocumentConverter()

    def _is_potentially_noise(self, text: str) -> bool:
        """
        Applies rule-based checks to flag likely academic noise.
        """

        text_lower = text.strip().lower()

        # Strip markdown formatting
        clean_text = text_lower.replace('#', '').strip()
        if clean_text in config.SCIENTIFIC_HEADERS:
            return False

        for pattern in config.NOISE_REGEX_PATTERNS:
            if pattern.search(text_lower):
                return True

        words = text_lower.split()
        if len(words) <= config.MIN_WORD_COUNT_THRESHOLD:
            return True

        return False

    def _extract_item_with_text_attr(self, item: NodeItem, level: int) -> tuple[str, str]:
        """
        Extracts raw text and applies Markdown formatting based on the layout label.
        """

        text = item.text.strip()
        if not text:
            return "", ""

        # Fix hyphenation across lines
        text = config.HYPHEN_WRAP_PATTERN.sub(r'\1\2', text)

        # Apply markdown formatting based on the label
        if item.label == DocItemLabel.SECTION_HEADER:
            md_content = f"{'#' * max(1, level)} {text}"
        elif item.label == DocItemLabel.LIST_ITEM:
            md_content = f"* {text}"
        else:
            md_content = text

        return text, md_content

    def _extract_block_text(
        self,
        doc: DoclingDocument,
        item: NodeItem,
        level: int
    ) -> tuple[str, str]:
        """
        Routes the document item to the correct extraction method based on its type.
        """

        if type(item).__name__ == "TableItem":
            text = item.export_to_markdown(doc=doc).strip()
            return text, text

        if hasattr(item, "text"):
            return self._extract_item_with_text_attr(item, level)

        return "", ""

    def _get_item_page_numbers(self, item: NodeItem) -> list[int]:
        """
        Extracts unique page numbers from the item's provenance metadata.
        """

        if hasattr(item, "prov") and item.prov:
            return list(set(p.page_no for p in item.prov if hasattr(p, "page_no")))

        return []

    def _extract_block(
        self,
        doc: DoclingDocument,
        item: NodeItem,
        level: int,
        seen_content: set[int]
    ) -> ParsedBlock | None:
        """
        Processes a single item, returning a ParsedBlock if it passes validity checks.
        """

        if item.label in config.EXCLUDED_DOCLING_LABELS:
            return None

        text, md_content = self._extract_block_text(doc, item, level)

        # Ensure text contains numbers or letters
        if not any(char.isalnum() for char in text):
            return None

        # Ensure text is new
        content_hash = hash(text)
        if content_hash in seen_content:
            return None
        seen_content.add(content_hash)

        page_numbers = self._get_item_page_numbers(item)
        return ParsedBlock(
            text=text,
            markdown=md_content,
            label=item.label.name,
            item_type=type(item).__name__,
            page_numbers=page_numbers,
            is_noise_risk=self._is_potentially_noise(text),
            level=level
        )

    def _call_curation_llm(self, user_prompt: str) -> dict:
        """
        Sends a text batch to the LLM and returns the parsed JSON curation results.
        """

        formatted_prompt = f"### INPUT DATA:\n{user_prompt}"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": config.LLM_CURATION_PROMPT},
                    {"role": "user", "content": formatted_prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=config.LLM_CURATION_MODEL_TEMPERATURE
            )

            response = chat_completion.choices[0].message.content
            clean_json = config.CODE_BLOCK_PATTERN.sub('', response).strip()

            return json.loads(clean_json)

        except Exception as e:
            # Return empty dict to prevent pipeline crashes on API timeouts or malformed JSON
            return {}

    def _get_noise_blocks(self, batch_text: str) -> list[int]:
        """
        Calls the LLM to identify noisy blocks and returns their integer IDs.
        """

        results = self._call_curation_llm(batch_text)
        return [int(bid) for bid in results if results[bid] == config.REMOVE_FLAG]

    def _remove_noise_blocks(self, blocks_reg: dict) -> dict:
        """
        Batches flagged blocks to the LLM for evaluation and filters out confirmed noise.
        """

        noise_risk_bids = [b for b in blocks_reg if blocks_reg[b].is_noise_risk]
        if not noise_risk_bids:
            return blocks_reg

        current_batch_text = ""
        bids_to_remove = []
        for bid in noise_risk_bids:
            block_text = blocks_reg[bid].text
            entry = f"\n=============\n[BID: {bid}]\n{block_text}\n"

            if len(current_batch_text) + len(entry) > config.LLM_BATCH_CHAR_LIMIT:
                bids_to_remove.extend(self._get_noise_blocks(current_batch_text))
                current_batch_text = ""

            current_batch_text += entry
            current_batch_count += 1

        # Catch the final, partially-filled batch
        if current_batch_text:
            bids_to_remove.extend(self._get_noise_blocks(current_batch_text))

        return {b: blocks_reg[b] for b in blocks_reg if b not in bids_to_remove}

    def extract_blocks(self, filepath: str) -> dict[int, ParsedBlock]:
        """
        Converts a PDF to structured blocks, filters duplicates, and removes academic noise.
        """

        blocks_reg = {}
        curr_bid = 0
        doc = self.converter.convert(filepath).document
        seen_content = set()

        for item, level in doc.iterate_items():
            block = self._extract_block(doc, item, level, seen_content)
            if block is not None:
                blocks_reg[curr_bid] = block
                curr_bid += 1

        return self._remove_noise_blocks(blocks_reg)

if __name__ == "__main__":
    parser = PdfParser()
    blocks = parser.extract_blocks("test_pdfs/jiy114.pdf")

    for b in blocks:
        print("\n---")
        print(f"**[BID: {b}]**")
        print(blocks[b].markdown)
        print("---\n")



