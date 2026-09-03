from app.domain.decisions.resolver import DecisionStrategyResolver
from app.domain.entities import AccessoryClassification, ClassificationContext
from app.domain.ports import AccessoryResearchPort
from app.domain.rules.resolver import RuleResolver


class AccessoryClassifier:
    """Coordinates research, rule evaluation, and the final decision.

    This class intentionally defines only the service boundary. The classification
    workflow will be implemented once the business rules have been approved.
    """

    def __init__(
        self,
        researcher: AccessoryResearchPort,
        rule_resolver: RuleResolver,
        strategy_resolver: DecisionStrategyResolver,
    ) -> None:
        self._researcher = researcher
        self._rule_resolver = rule_resolver
        self._strategy_resolver = strategy_resolver

    async def classify(
        self,
        accessory_name: str,
        context: ClassificationContext,
    ) -> AccessoryClassification:
        raise NotImplementedError("Accessory classification is not implemented yet")
