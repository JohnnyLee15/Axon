from src.trackers.document_state import ParsedDoc

def get_active_ids(parsed_doc: ParsedDoc) -> str:
    active_ids = []
    if parsed_doc.doi:
        active_ids.append(f"DOI: {parsed_doc.doi}")

    if parsed_doc.arxiv:
        active_ids.append(f"arXiv: {parsed_doc.arxiv}")

    if parsed_doc.pmcid:
        active_ids.append(f"PMCID: {parsed_doc.pmcid}")

    if parsed_doc.pmid:
        active_ids.append(f"PMID: {parsed_doc.pmid}")

    return  ", ".join(active_ids) if active_ids else "Unknown identifiers"