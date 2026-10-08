from pydantic import ValidationError


class LLMError(Exception):
    """Provider or transport failure.

    The message is sanitized and safe to return to API callers; raw response
    bodies are excluded. The original exception, if any, is chained as
    ``__cause__`` so it remains available in server logs.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ModelsNotFoundError(LLMError):
    def __init__(self, models: tuple[str, ...]) -> None:
        self.models = models
        super().__init__(
            f"None of the requested models were found: {', '.join(models)}"
        )


class LLMTimeoutError(LLMError):
    """A request exceeded its deadline."""


class LLMResponseError(LLMError):
    """Malformed, refused, unsupported, or incomplete provider response."""


class UnsupportedLLMToolError(LLMError):
    """The selected model or provider cannot use a requested tool."""

    def __init__(
        self, tool: str, model: str, *, status_code: int | None = None
    ) -> None:
        self.tool = tool
        self.model = model
        super().__init__(
            f"Model '{model}' does not support the '{tool}' tool",
            status_code=status_code,
        )


def summarize_validation_error(error: ValidationError) -> str:
    """Describe which fields failed and why, without echoing the invalid input."""
    return "; ".join(
        f"{'.'.join(map(str, item['loc'])) or 'response'}: {item['msg']}"
        for item in error.errors(include_input=False, include_url=False)
    )
