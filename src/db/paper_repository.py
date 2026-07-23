from src.ingestion.models import ParsedDocument

from .sqlite_database import SQLiteDatabase
from .schema_manager import PAPER_TABLE, LSH_TABLE


class PaperRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database


    def metadata_exists(self, parsed_doc: ParsedDocument) -> bool:
        sql = f"""
            SELECT 1
            FROM {PAPER_TABLE}
            WHERE doi = ?
                OR arxiv = ?
                OR pmcid = ?
                OR pmid = ?
            LIMIT 1;
        """

        params = (parsed_doc.doi, parsed_doc.arxiv, parsed_doc.pmcid, parsed_doc.pmid)

        with self._database.connect() as connection:
            row = connection.execute(sql, params).fetchone()

        return row is not None


    def get_lsh_candidates(self, band_hashes: list[int]) -> list[tuple[int, bytes]]:
        if not band_hashes:
            return []

        band_conds = " OR ".join(
            f"(l.band_idx = {i} AND l.band_hash = ?)"
            for i in range(len(band_hashes))
        )

        sql = f"""
            SELECT DISTINCT p.id, p.minhash_sig
            FROM {PAPER_TABLE} p
            JOIN {LSH_TABLE} l ON p.id = l.paper_id
            WHERE {band_conds};
        """

        with self._database.connect() as connection:
            rows = connection.execute(sql, band_hashes).fetchall()

        return rows


    def insert_paper(
        self,
        parsed_doc: ParsedDocument,
        minhash_sig: bytes,
        band_hashes: list[int]
    ) -> int:
        paper_stmt = f"""
            INSERT INTO {PAPER_TABLE} (
                title,
                doi,
                arxiv,
                pmcid,
                pmid,
                minhash_sig
            )
            VALUES (?, ?, ?, ?, ?, ?);
        """

        lsh_stmt = f"""
            INSERT INTO {LSH_TABLE} (
                paper_id,
                band_idx,
                band_hash
            )
            VALUES (?, ?, ?);
        """

        paper_params = (
            parsed_doc.title,
            parsed_doc.doi,
            parsed_doc.arxiv,
            parsed_doc.pmcid,
            parsed_doc.pmid,
            minhash_sig,
        )

        with self._database.connect() as connection:
            paper_id = connection.execute(paper_stmt, paper_params).lastrowid
            lsh_params = [(paper_id, i, h) for i, h in enumerate(band_hashes)]
            connection.executemany(lsh_stmt, lsh_params)

        return paper_id


    def delete_all_papers(self) -> None:
        sql = f"DELETE FROM {PAPER_TABLE};"
        with self._database.connect() as connection:
            connection.execute(sql)


    def get_metadata_by_ids(self, ids: list[int]) -> list[tuple]:
        if not ids:
            return []

        place_holders = ", ".join("?" for _ in ids)
        sql = f"""
        SELECT
            title,
            doi,
            arxiv,
            pmcid,
            pmid
        FROM {PAPER_TABLE}
        WHERE id IN ({place_holders})
        """
        params = (*ids,)

        with self._database.connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return rows
