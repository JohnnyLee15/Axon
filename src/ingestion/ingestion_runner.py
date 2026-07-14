import time
from pathlib import Path

from src.db.vector_database import VectorDatabase, INVALID_PAPER_ID
from src.db.min_hasher import MinHasher
from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis
from src.utils.paper_utils import get_active_ids

from .pdf_parser import PdfParser
from .models import ParsedDocument
from .semantic_chunker import SemanticChunker


JACCARD_SIMILARITY_THRESHOLD = 0.84


class IngestionRunner:
    def __init__(
        self,
        parser: PdfParser,
        chunker: SemanticChunker,
        db: VectorDatabase,
        minhasher: MinHasher,
        ui: AxonUI,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._db = db
        self._minhasher = minhasher
        self._ui = ui


    def _format_time(self, start_time: float, end_time: float) -> str:
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time * 1000) % 1000)
        return f"{minutes:02d}m {seconds:02d}s {milliseconds:03d}ms"


    def _get_pdf_filepaths(self, filepath: Path) -> list[Path]:
        pdf_files = []
        if filepath.is_file():
            pdf_files = [filepath] if filepath.suffix.lower() == ".pdf" else []
        elif filepath.is_dir():
            pdf_files = list(filepath.rglob("*.pdf"))

        if not pdf_files:
            self._ui.warning(f"No PDF files found at: \"{emphasis(filepath)}\".")

        return pdf_files


    def _get_filepath(self, filepath: str) -> Path | None:
        try:
            filepath = Path(filepath).expanduser().resolve()
        except Exception as e:
            self._ui.error(f"OS Error resolving path \"{emphasis(filepath)}\": {e}.")
            return None

        if not filepath.exists():
            self._ui.error(f"Path not found: \"{emphasis(filepath)}\".")
            return None

        return filepath


    def _compare_min_hashes(self, sig_bytes: bytes, lsh_cands: list[tuple[int, bytes]]) -> bool:
        for cand_pid, cand_sig_bytes in lsh_cands:
            jaccard_estimate = self._minhasher.estimate_jaccard(sig_bytes, cand_sig_bytes)
            if jaccard_estimate >= JACCARD_SIMILARITY_THRESHOLD:
                id_str = f"ID: {cand_pid}"
                similarity_str = f"Similarity: {jaccard_estimate:.3f}"
                self._ui.warning(
                    "Duplicate content detected "
                    f"({emphasis(id_str)}, {emphasis(similarity_str)}). Skipping."
                )
                return True

        return False


    def _is_eligible_for_processing(self, parsed_doc: ParsedDocument) -> bool:
        if not parsed_doc.full_raw_text:
            self._ui.warning("Could not extract valid text. Skipping.")
            return False

        if not (
            parsed_doc.doi or
            parsed_doc.arxiv or
            parsed_doc.pmcid or
            parsed_doc.pmid
        ):
            return True

        exists = self._db.metadata_exists(parsed_doc)
        if exists is None:
            return False

        if exists:
            id_str = get_active_ids(parsed_doc)
            self._ui.warning(f"Duplicate metadata detected ({emphasis(id_str)}). Skipping.")
            return False

        return True


    def _ingest_paper(self, parsed_doc: ParsedDocument) -> int:
        sig_bytes, band_hashes = self._minhasher.minhash_doc(parsed_doc.full_raw_text)
        if sig_bytes is None or band_hashes is None:
            self._ui.warning("Document too short to fingerprint. Skipping.")
            return INVALID_PAPER_ID

        lsh_cands = self._db.get_lsh_candidates(band_hashes)
        if lsh_cands is None:
            return INVALID_PAPER_ID

        is_duplicate = self._compare_min_hashes(sig_bytes, lsh_cands)
        if is_duplicate:
            return INVALID_PAPER_ID

        pid = self._db.insert_paper(parsed_doc, sig_bytes, band_hashes)
        return pid


    def _process_pdf(self, pdf_path: Path) -> int | None:
        parsed_doc = self._parser(pdf_path)
        can_process = self._is_eligible_for_processing(parsed_doc)
        if not can_process:
            return

        pid = self._ingest_paper(parsed_doc)
        if pid == INVALID_PAPER_ID:
            return

        self._ui.progress("Generating semantic chunks and embeddings")
        chunks = self._chunker(parsed_doc.blocks_reg)
        self._ui.success(f"Successfully generated {emphasis(len(chunks))} chunks.")
        self._db.insert_paper_chunks(chunks, pid)

        return pid


    def _load_pdf(self, pdf_path: Path) -> None:
        self._ui.display_section(pdf_path.name)
        start_time = time.perf_counter()
        pid = self._process_pdf(pdf_path)
        if pid is None:
            return

        end_time = time.perf_counter()
        time_str = self._format_time(start_time, end_time)
        pid_str = f"ID: {pid}"
        self._ui.success(
            f"Paper ingested successfully ({emphasis(pid_str)}) in {emphasis(time_str)}."
        )


    def load_pdfs(self, filepath: str) -> None:
        filepath = self._get_filepath(filepath)
        if filepath is None:
            return

        pdf_files = self._get_pdf_filepaths(filepath)
        if not pdf_files:
            return

        num_pdf_files = f"{len(pdf_files)} PDF files"
        self._ui.progress(f"Starting Axon Ingestion Pipeline ({emphasis(num_pdf_files)}).")
        for pdf_path in pdf_files:
            self._load_pdf(pdf_path)
