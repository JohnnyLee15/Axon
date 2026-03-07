class ParsedBlock:
    """
    Represents a structured block of content extracted from a PDF document.
    Serves as the standard data object passed to the semantic chunker.
    """

    def __init__(
        self,
        markdown: str,
        label: str,
        item_type: str,
        page_numbers: list[int],
        is_noise_risk: bool,
    ) -> None:
        self.markdown = markdown
        self.label = label
        self.item_type = item_type
        self.page_numbers = page_numbers
        self.is_noise_risk = is_noise_risk