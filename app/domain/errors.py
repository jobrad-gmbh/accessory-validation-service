class ValidationConfigurationError(ValueError):
    """The configured validation process is invalid."""


class ValidationExecutionError(Exception):
    """A validation could not be completed.

    The original error is always chained as ``__cause__``.
    """

    def __init__(self, validation_id: str, cause: BaseException) -> None:
        self.validation_id = validation_id
        super().__init__(
            f"Validation {validation_id} failed: {type(cause).__name__}: {cause}"
        )


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
