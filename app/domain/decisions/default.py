from app.domain.decisions.base import DecisionStrategy


class DefaultDecisionStrategy(DecisionStrategy):
    name = "default"
    required_rules: tuple[str, ...] = (
        "explicitly_excluded",
        "traffic_law_required",
        "permanently_attached",
    )

    def try_decide(self, results: dict[str, bool]) -> bool | None:
        raise NotImplementedError("Default decision strategy is not implemented yet")

    def final_decision(self, results: dict[str, bool]) -> bool:
        raise NotImplementedError("Default final decision is not implemented yet")
