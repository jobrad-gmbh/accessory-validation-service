from app.domain.ports import LLMPort


class LLMClient(LLMPort):
    """Placeholder adapter for the future company LLM connection."""

    def __init__(self, base_url: str, model: str | None) -> None:
        self._base_url = base_url
        self._model = model

    async def ask_boolean(self, question: str, description: str) -> bool:
        raise NotImplementedError("LLM integration is not implemented yet")
