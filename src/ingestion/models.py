from dataclasses import dataclass


@dataclass
class Chunk:
    markdown: str
    embedding: list[float] | None = None


@dataclass
class Block:
    markdown: str
    label: str
    is_noise_risk: bool


@dataclass
class ParsedDocument:
    blocks_reg: dict[int, Block]
    full_raw_text: str
    page_one: str
    title: str | None = None
    doi: str | None = None
    pmcid: str | None = None
    pmid: str | None = None
    arxiv: str | None = None