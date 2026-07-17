BLOCK_CURATION_PROMPT = """You are a Data Curation Expert for a Scientific RAG (Retrieval-Augmented Generation) pipeline.
Your task is to classify text blocks extracted from PDF research papers as either "Signal" (Keep) or "Noise" (Remove).

The input contains text blocks wrapped in <block id="x"> tags, all enclosed within an <input_blocks> parent tag.
Analyze the provided blocks and identify the IDs of the blocks that should be REMOVED (marked as noise).

### CRITERIA FOR CLASSIFICATION

**KEEP (Signal) - Do NOT include these IDs in your response:**
1. **Section Headers:** Any standard scientific header (e.g., "Abstract", "Introduction", "Results", "Methods", "Conclusion", "References", "Funding"). **CRITICAL: Do not remove headers.**
2. **Body Text:** Sentences or paragraphs that look like part of the scientific narrative (even if short).
3. **Figure/Table Captions:** Text describing a figure or table (e.g., "Figure 1: Correlation between...").
4. **Formulas/Data:** Mathematical equations or specific data points integral to the paper.

**REMOVE (Noise) - Include these IDs in your response:**
1. **Running Headers/Footers:** Journal names, page numbers (e.g., "Page 1 of 5"), dates, or repeated titles at the top/bottom of pages.
2. **Metadata artifacts:** "Downloaded from...", DOIs, URLs, "Copyright © 2024", "All rights reserved".
3. **Correspondence info:** Author emails, fax numbers, or address blocks (unless part of the main text body).
4. **Navigation garbage:** "Back to top", "Next page", or isolated random symbols.
5. **References/Bibliography:** The list of citations at the end of the paper. (Note: Keep the "References" header itself if you want to know where it starts, but remove the list items).

### INPUT FORMAT
<input_blocks>
<block id='<integer>'>
<text content>
</block>
...
</input_blocks>

**ACTION REQUIRED:** Return a JSON object containing the array of BIDs you have identified as Noise under the key `noise_block_ids`. Do not include Signal IDs.
"""

NOISE_BLOCK_IDS_KEY = "noise_block_ids"
BLOCK_CURATION_SCHEMA = {
    "type": "object",
    "properties": {
        NOISE_BLOCK_IDS_KEY: {
            "type": "array",
            "items": {"type": "integer"},
            "description": "List of BIDs (Block IDs) that should be removed based on the curation criteria."
        }
    },
    "required": [NOISE_BLOCK_IDS_KEY]
}

TITLE_EXTRACTION_PROMPT = """Extract the main article title from the raw text of the FIRST PAGE of a scientific PDF.
The raw text will be provided inside <first_page_text> XML tags.

Return only the article title if it can be identified from the first page.

Extraction rules:
1. Extract the main article title only.
2. Do NOT return the journal name, running header, author names, affiliations, correspondence text, abstract heading, footer text, page numbers, dates, or section headings.
3. Reconstruct a multi-line title into one clean string with single spaces.
4. If the title cannot be confidently identified, return null.
5. Do not guess, infer, or fabricate anything.
6. Never return anything except the title field in the JSON response.
"""

TITLE_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Main article title, cleaned and reconstructed into one line",
            "nullable": True
        }
    },
    "required": ["title"]
}

