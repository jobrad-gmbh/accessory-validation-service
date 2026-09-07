from abc import ABC, abstractmethod
from typing import Protocol, final

from app.domain.validation.errors import (
    ValidationConfigurationError,
    ValidationExecutionError,
)
from app.domain.validation.request import ValidationRequest
from app.domain.validation.results import ValidationExecution, ValidationResult
from app.shared.decision_strategies.contracts import StrategySelector
from app.shared.decision_strategies.errors import (
    StrategyConfigurationError,
    StrategyExecutionError,
    StrategySelectionError,
)
from app.shared.decision_strategies.evaluator import DecisionTreeEvaluator
from app.shared.decision_strategies.results import StrategyEvaluation


class Validation(Protocol):
    """An independent business check with a stable id."""

    @property
    def id(self) -> str: ...

    async def validate(self, request: ValidationRequest) -> ValidationExecution: ...


class SimpleValidation(ABC):
    """Build an execution around a validation that uses no strategy."""

    id: str

    @final
    async def validate(self, request: ValidationRequest) -> ValidationExecution:
        result = await self.evaluate_result(request)
        return ValidationExecution(
            product=request.product,
            validation_id=self.id,
            result=result,
        )

    @abstractmethod
    async def evaluate_result(self, request: ValidationRequest) -> ValidationResult: ...


class StrategyBasedValidation(ABC):
    """Execute and capture a strategy as part of its owning validation."""

    id: str

    def __init__(
        self,
        selector: StrategySelector[ValidationRequest],
        evaluator: DecisionTreeEvaluator[ValidationRequest],
    ) -> None:
        self._selector = selector
        self._evaluator = evaluator

    @final
    async def validate(self, request: ValidationRequest) -> ValidationExecution:
        try:
            strategy = self._selector.select(request)
            evaluation = await self._evaluator.evaluate(strategy, request)
        except (StrategySelectionError, StrategyConfigurationError) as exc:
            raise ValidationConfigurationError(
                f"No unambiguous strategy is configured for validation {self.id}"
            ) from exc
        except StrategyExecutionError as exc:
            raise ValidationExecutionError(
                f"Strategy evaluation failed for validation {self.id}"
            ) from exc

        result = self.result_from_strategy(evaluation)
        return ValidationExecution(
            product=request.product,
            validation_id=self.id,
            result=result,
            strategy_evaluations=(evaluation,),
        )

    @abstractmethod
    def result_from_strategy(self, evaluation: StrategyEvaluation) -> ValidationResult: ...
