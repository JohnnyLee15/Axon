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
        is_noise_risk: bool,
    ) -> None:
        self.markdown = markdown
        self.label = label
        self.item_type = item_type
        self.is_noise_risk = is_noise_risk