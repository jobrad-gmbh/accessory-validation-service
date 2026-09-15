class LlmError(Exception):
    """An LLM request failed."""


class LlmHttpError(LlmError):
    """The LLM endpoint returned an unsuccessful HTTP status."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"The LLM service returned HTTP {status_code}")
        self.status_code = status_code


class LlmTimeoutError(LlmError):
    """The LLM request exceeded its deadline."""


class LlmResponseError(LlmError):
    """The LLM returned an unusable response."""
