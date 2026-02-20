import fitz
import re
import os
import json
from groq import Groq

class pdf_parser:
    # Constants
    HEADER_RATIO = 0.08
    FOOTER_RATIO = 0.95
    FOOTER_RATIO_LLM = 0.90
    SIDEBAR_RATIO = 0.90
    COLUMN_TOLERANCE_RATIO = 0.02
    BLOCK_WORD_CUTOFF = 10
    BLOCK_WORD_CUTOFF_LLM = 15
    NARROW_WIDTH_RATIO = 0.20
    MAX_CHARS_LLM = 4000

    CORE_HEADERS = {
        "abstract", "introduction", "background", "objectives", "aims",
        "methods", "methodology", "materials and methods",
        "experimental procedures", "study design", "results", "findings",
        "discussion", "conclusion", "conclusions", "summary"
    }

    FLUFF_PATTERNS = [
        r'downloaded\s+from',
        r'https?://\S+',
        r'doi:?\s*10\.',
        r'vol(ume)?\.?\s*\d+',
        r'no\.?\s*\d+',
        r'pp\.?\s*\d+',
        r'©', r'copyright',
        r'all rights reserved',
        r'received\s+\d+',
        r'accepted\s+\d+',
        r'published\s+online',
        r'email:', r'correspondence:',
        r'issn\s+\d+',
        r'keywords\.',
    ]

    SYSTEM_PROMPT = """
        You are a Data Curation Expert for a Scientific RAG (Retrieval-Augmented Generation) pipeline.
        Your task is to classify text blocks extracted from PDF research papers as either "Signal" (Keep) or "Noise" (Remove).

        The input contains text blocks marked with IDs (e.g., [BID: 12]).
        You must output a JSON object mapping the BID to a binary flag:
        - 1 (KEEP): Valid content.
        - 0 (REMOVE): Fluff/Noise.

        ### CRITERIA FOR CLASSIFICATION

        **MARK AS 1 (KEEP - Signal):**
        1. **Section Headers:** Any standard scientific header (e.g., "Abstract", "Introduction", "Results", "Methods", "Conclusion", "References", "Funding"). **CRITICAL: Do not remove headers.**
        2. **Body Text:** Sentences or paragraphs that look like part of the scientific narrative (even if short).
        3. **Figure/Table Captions:** Text describing a figure or table (e.g., "Figure 1: Correlation between...").
        4. **Formulas/Data:** Mathematical equations or specific data points integral to the paper.

        **MARK AS 0 (REMOVE - Noise):**
        1. **Running Headers/Footers:** Journal names, page numbers (e.g., "Page 1 of 5"), dates, or repeated titles at the top/bottom of pages.
        2. **Metadata artifacts:** "Downloaded from...", DOIs, URLs, "Copyright © 2024", "All rights reserved".
        3. **Correspondence info:** Author emails, fax numbers, or address blocks (unless part of the main text body).
        4. **Navigation garbage:** "Back to top", "Next page", or isolated random symbols.
        5. **References/Bibliography:** The list of citations at the end of the paper. (Note: Keep the "References" header itself if you want to know where it starts, but remove the list items).

        ### INPUT FORMAT
        Each block is separated by "=============".
        [BID: <integer>]
        <text content>

        ### OUTPUT FORMAT
        Return ONLY a valid JSON object. Do not include markdown formatting or explanations.
        Example:
        {
            "12": 0,
            "45": 1
        }
        """

    def __init__(self):
        self.model = "llama-3.3-70b-versatile"
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def is_fluff(self, block, pw, ph):
        x0, y0, _, y1, text, _, _ = block

        if y1 < (self.HEADER_RATIO * ph):
            return True
        if y0 > (self.FOOTER_RATIO * ph):
            return True
        if x0 > (self.SIDEBAR_RATIO * pw):
            return True

        words = text.split()
        if len(words) <= self.BLOCK_WORD_CUTOFF:
            clean_text = re.sub(r'^[\d\.\s]+', '', text).strip().lower()
            if clean_text in self.CORE_HEADERS:
                return False

            for word in words:
                clean_word = re.sub(r'[^\w]', '', word).lower()
                if clean_word in self.CORE_HEADERS:
                    return False

            return True
        return False

    def is_potentially_fluff(self, block, pw, ph):
        x0, y0, x1, y1, text, _, _ = block
        if y0 > (ph * self.FOOTER_RATIO_LLM):
            return True

        bw = x1 - x0
        bh = y1 - y0
        if bw < (self.NARROW_WIDTH_RATIO * pw):
            return True

        text_lower = text.strip().lower()
        for pattern in self.FLUFF_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        words = text_lower.split()

        if len(words) <= self.BLOCK_WORD_CUTOFF_LLM:
            return True

        return False

    def sort_blocks(self, blocks, pw):
        blocks.sort(key=lambda b: b[0])
        groups = []

        for b in blocks:
            if not groups:
                groups.append([b])
                continue

            x0 = b[0]
            group_x0 = groups[-1][0][0]
            if abs(x0 - group_x0) <= (self.COLUMN_TOLERANCE_RATIO * pw):
                groups[-1].append(b)
            else:
                groups.append([b])

        for g in groups:
            g.sort(key=lambda b: b[1])

        groups.sort(key=lambda g : g[0][0])
        return [b for g in groups for b in g]

    def get_pdf_blocks(self, filepath):
        block_reg = {}
        curr_bid = 0
        with fitz.open(filepath) as doc:
            for page in doc:
                pw = page.rect.width
                ph = page.rect.height
                blocks = page.get_text(option="blocks")
                blocks = self.sort_blocks(blocks, pw)
                blocks = [b for b in blocks if not self.is_fluff(b, pw, ph)]
                for b in blocks:
                    x0, y0, x1, y1, text, block_no, block_type = b
                    text = re.sub(r'([A-Za-z]+)-\s*\n\s*([a-z]+)', r'\1\2', text)
                    b = (x0, y0, x1, y1, text, block_no, block_type)
                    block_reg[curr_bid] = {
                        "block": b,
                        "is_fluff": self.is_potentially_fluff(b, pw, ph)
                    }
                    curr_bid += 1

        return block_reg

    def call_llm(self, user_prompt):
        user_prompt = f"### INPUT DATA:\n{user_prompt}"
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
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


    def remove_fluff_blocks(self, blocks_reg):
        fluff_bids = [b for b in blocks_reg if blocks_reg[b]["is_fluff"]]
        if not fluff_bids:
            return blocks_reg

        current_batch_text = ""
        bids_to_remove = []
        for bid in fluff_bids:
            block_text = blocks_reg[bid]["block"][4]
            entry = f"\n=============\n"
            entry += f"[BID: {bid}]\n"
            entry += f"{block_text}\n"

            if len(current_batch_text) + len(entry) > self.MAX_CHARS_LLM:
                results = self.call_llm(current_batch_text)
                bids_to_remove.extend(int(bid) for bid in results if results[bid] == 0)
                current_batch_text = ""

            current_batch_text += entry

        if current_batch_text:
            results = self.call_llm(current_batch_text)
            bids_to_remove.extend(int(bid) for bid in results if results[bid] == 0)

        clean_reg = {}
        for b in blocks_reg:
            if b not in bids_to_remove:
                clean_reg[b] = blocks_reg[b]["block"]

        return clean_reg


if __name__ == "__main__":
    parser = pdf_parser()
    blocks = parser.get_pdf_blocks("test_pdfs/jiy114.pdf")
    blocks = parser.remove_fluff_blocks(blocks)

    for b in blocks:
        print(f"\n[BID: {b}]")
        print(blocks[b][4])



