import re
from typing import Callable

import pysbd
from docling.datamodel.base_models import DocItemLabel

from .chunk_tracker import ChunkTracker
from .models import Block, Chunk


MAX_HEADER_CHARS = 250
MAX_HEADER_STACK_CHARS = 600
MIN_CHUNK_CHARS = 300
MAX_CHUNK_CHARS = 1500
WHITESPACE_CUT_PATTERN = re.compile(r'.*(\s)')


class SemanticChunker:
    def __init__(self) -> None:
        self._segmenter = pysbd.Segmenter(language="en", clean=False)


    def __call__(self, blocks: dict[int, Block]) -> dict[int, Chunk]:
        return self._build_chunks(blocks)


    def _add_spacer(self, curr_len: int, text: str, spacer: str) -> str:
        return (spacer if curr_len > 0 else "") + text


    def _find_ws_cut_idx(
        self,
        tracker: ChunkTracker,
        sentence: str,
        start_idx: int,
        end_idx: int
    ) -> tuple[int, int]:
        ws_match = WHITESPACE_CUT_PATTERN.search(sentence[start_idx:end_idx])
        if not ws_match:
            return end_idx, end_idx

        last_ws_idx = start_idx + ws_match.start(1)
        ws_cand = self._add_spacer(len(tracker), sentence[start_idx:last_ws_idx], spacer=" ")

        if len(tracker) + len(ws_cand) >= MIN_CHUNK_CHARS:
            return last_ws_idx, last_ws_idx + 1

        return end_idx, end_idx


    def _split_sentence(self, tracker: ChunkTracker, sentence: str) -> None:
        start_idx = 0
        while start_idx < len(sentence):
            spacer_len = 1 if len(tracker) > 0 else 0
            end_idx = start_idx + MAX_CHUNK_CHARS - len(tracker) - spacer_len

            if end_idx >= len(sentence):
                tracker.add_text(self._add_spacer(len(tracker), sentence[start_idx:], spacer=" "))
                return

            cut_idx, next_start = self._find_ws_cut_idx(tracker, sentence, start_idx, end_idx)
            tracker.add_text(self._add_spacer(len(tracker), sentence[start_idx:cut_idx], spacer=" "))
            start_idx = next_start
            tracker.flush()


    def _add_or_split(
        self, tracker: ChunkTracker,
        text: str,
        split: Callable
    ) -> None:
        if len(tracker) >= MIN_CHUNK_CHARS:
            tracker.flush()

        if tracker.is_empty() and len(text) <= MAX_CHUNK_CHARS:
            tracker.add_text(text)
            return

        split(tracker, text)


    def _split_block(self, tracker: ChunkTracker, block_text: str) -> None:
        sentences = self._segmenter.segment(block_text)
        for sentence in sentences:
            cand_text = self._add_spacer(len(tracker), sentence, spacer=" ")

            if len(tracker) + len(cand_text) <= MAX_CHUNK_CHARS:
                tracker.add_text(cand_text)
            else:
                self._add_or_split(tracker, sentence, self._split_sentence)


    def _process_body(self, tracker: ChunkTracker, block_text: str) -> None:
        cand_text = self._add_spacer(len(tracker), block_text, spacer="\n\n")
        if len(tracker) + len(cand_text) <= MAX_CHUNK_CHARS:
            tracker.add_text(cand_text)
        else:
            self._add_or_split(tracker, block_text, self._split_block)


    def _should_flush_tracker(self, tracker: ChunkTracker, cand_header: str) -> bool:
        if len(tracker) >= MIN_CHUNK_CHARS and not tracker.last_was_header():
            return True

        return (
            tracker.last_was_header() and
            len(tracker) + len(cand_header) > MAX_HEADER_STACK_CHARS
        )


    def _process_header(self, tracker: ChunkTracker, block_text: str) -> None:
        cand_header = self._add_spacer(len(tracker), block_text, spacer="\n\n")
        if self._should_flush_tracker(tracker, cand_header):
            tracker.flush()
            cand_header = block_text

        tracker.add_text(cand_header, True)


    def _is_header(self, block: Block) -> bool:
        return (
            block.label == DocItemLabel.SECTION_HEADER.name and
            len(block.markdown) <= MAX_HEADER_CHARS
        )


    def _build_chunks(self, blocks_reg: dict[int, Block]) -> dict[int, Chunk]:
        tracker = ChunkTracker()
        for bid in sorted(blocks_reg):
            block = blocks_reg[bid]

            if self._is_header(block):
                self._process_header(tracker, block.markdown)
            else:
                self._process_body(tracker, block.markdown)

        tracker.flush()
        return tracker.get_chunks()
