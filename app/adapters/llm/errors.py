class LLMError(Exception):
    """Sanitized provider or transport failure; raw response bodies are excluded."""

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
