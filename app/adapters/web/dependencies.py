from typing import Annotated

from fastapi import Depends

from app.adapters.llm.client import LLMClient
from app.adapters.research.searxng import SearxngAccessoryResearch
from app.config.settings import settings
from app.domain.accessory_classifier import AccessoryClassifier
from app.domain.decisions.resolver import DecisionStrategyResolver
from app.domain.rules.resolver import RuleResolver


def get_accessory_classifier() -> AccessoryClassifier:
    """Construct the application service from its ports and adapters."""
    llm = LLMClient(settings.LLM_BASE_URL, settings.LLM_MODEL)
    researcher = SearxngAccessoryResearch(settings.SEARXNG_BASE_URL)
    return AccessoryClassifier(
        researcher=researcher,
        rule_resolver=RuleResolver(llm),
        strategy_resolver=DecisionStrategyResolver(),
    )


AccessoryClassifierDependency = Annotated[
    AccessoryClassifier,
    Depends(get_accessory_classifier),
]
