class ValidationConfigurationError(ValueError):
    """The configured validation process is invalid."""


class ValidationExecutionError(Exception):
    """A technical failure prevented validation."""


class ProductResolutionError(Exception):
    """A technical failure prevented product resolution."""


class ProductInformationRetrievalError(Exception):
    """Product information could not be retrieved reliably."""


class WebSearchNotSupportedError(ProductInformationRetrievalError):
    """The selected LLM model cannot perform the required web search."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(
            f"The selected model '{model}' does not support web search. "
            "Choose a web-search-capable model or disable web search."
        )
