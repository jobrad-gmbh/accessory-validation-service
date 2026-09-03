from app.domain.ports import AccessoryResearchPort


class SearxngAccessoryResearch(AccessoryResearchPort):
    """Placeholder adapter for future SearXNG integration."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def research(self, accessory_name: str) -> str:
        raise NotImplementedError("SearXNG integration is not implemented yet")
