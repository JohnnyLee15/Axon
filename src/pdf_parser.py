import re
import os
import json
from groq import Groq
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocItemLabel
import config

class PdfParser:
    def __init__(self):
        self.model = "llama-3.3-70b-versatile"
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.converter = DocumentConverter()

    def is_potentially_noise(self, text):
        text_lower = text.strip().lower()

        clean_text = text_lower.replace('#', '').strip()
        if clean_text in config.SCIENTIFIC_HEADERS:
            return False

        for pattern in config.NOISE_REGEX_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        words = text_lower.split()
        if len(words) <= config.MIN_WORD_COUNT_THRESHOLD:
            return True

        return False

    def extract_blocks(self, filepath):
        block_reg = {}
        curr_bid = 0
        doc = self.converter.convert(filepath).document
        seen_content = set()
        for item, level in doc.iterate_items():
            if item.label in config.EXCLUDED_DOCLING_LABELS:
                continue

            item_type = type(item).__name__
            text = ""
            md_content = ""

            if item_type == "TableItem":
                text = item.export_to_markdown(doc=doc).strip()
                md_content = text


            elif hasattr(item, "text"):
                text = item.text.strip()
                if not text:
                    continue

                text = re.sub(r'([A-Za-z]+)-\s*\n\s*([a-z]+)', r'\1\2', text)

                if item.label == DocItemLabel.SECTION_HEADER:
                    md_content = f"{'#' * max(1, level)} {text}"
                elif item.label == DocItemLabel.LIST_ITEM:
                    md_content = f"* {text}"
                else:
                    md_content = text
            else:
                continue

            if not text or not any(char.isalnum() for char in text) or text == "":
                continue

            content_hash = hash(text)
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            page_numbers = []
            if hasattr(item, "prov") and item.prov:
                page_numbers = list(set(p.page_no for p in item.prov if hasattr(p, "page_no")))

            block_reg[curr_bid] = {
                "text": text,
                "markdown": md_content,
                "label": item.label.name,
                "item_type": item_type,
                "page_numbers": page_numbers,
                "is_noise_risk": self.is_potentially_noise(text),
                "level": level
            }
            curr_bid += 1

        return block_reg

    def call_llm(self, user_prompt):
        user_prompt = f"### INPUT DATA:\n{user_prompt}"
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": config.LLM_CURATION_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                model = self.model,
                response_format={"type": "json_object"},
                temperature=0.0
            )

            response = chat_completion.choices[0].message.content
            clean_json = re.sub(r'```(?:json)?\n?|```', '', response).strip()
            return json.loads(clean_json)

        except Exception as e:
            return {}

    def get_noise_blocks(self, batch_text):
        results = self.call_llm(batch_text)
        return [int(bid) for bid in results if results[bid] == config.REMOVE_FLAG]


    def remove_noise_blocks(self, blocks_reg):
        fluff_bids = [b for b in blocks_reg if blocks_reg[b]["is_noise_risk"]]
        if not fluff_bids:
            return blocks_reg

        current_batch_text = ""
        bids_to_remove = []
        for bid in fluff_bids:
            block_text = blocks_reg[bid]["text"]
            entry = f"\n=============\n"
            entry += f"[BID: {bid}]\n"
            entry += f"{block_text}\n"

            if len(current_batch_text) + len(entry) > config.LLM_BATCH_CHAR_LIMIT:
                bids_to_remove.extend(self.get_noise_blocks(current_batch_text))
                current_batch_text = ""

            current_batch_text += entry

        if current_batch_text:
            bids_to_remove.extend(self.get_noise_blocks(current_batch_text))

        clean_reg = {}
        for b in blocks_reg:
            if b not in bids_to_remove:
                clean_reg[b] = blocks_reg[b]

        return clean_reg

if __name__ == "__main__":
    parser = PdfParser()
    blocks = parser.extract_blocks("test_pdfs/jiy114.pdf")
    blocks = parser.remove_noise_blocks(blocks)

    for b in blocks:
        print("\n---")
        print(f"**[BID: {b}]**")
        print(blocks[b]["markdown"])
        print("---\n")



