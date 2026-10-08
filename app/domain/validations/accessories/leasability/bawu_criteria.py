"""BW variants of only the criteria whose standard rules differ for BW."""

from pathlib import Path

from app.adapters.llm import LLMClient, LLMModelSettings
from app.domain.criterion import CriterionResult
from app.domain.validation import ValidationRequest
from app.domain.validations.accessories.leasability.criteria import (
    ExplicitlyLeasableAccessoryTypeCriterion,
    ExplicitlyNotLeasableAccessoryTypeCriterion,
    FunctionalUnitWithBicycleCriterion,
    SpecialRulesCriterion,
    _CriterionResponse,
    _generate_structured_response,
)
from app.domain.validations.accessories.product_information import AccessoryProductInformation

PROMPTS = Path(__file__).with_name("prompts") / "bawu"


class _BawuPromptCriterion:
    """Reuse standard initialization and IDs, selecting the amended BW prompt."""

    id: str
    _llm_client: LLMClient

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client, request, product_information,
            PROMPTS / f"{self.id}.md", _CriterionResponse, settings, self.id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class BawuExplicitlyNotLeasableAccessoryTypeCriterion(
    _BawuPromptCriterion, ExplicitlyNotLeasableAccessoryTypeCriterion
):
    pass


class BawuExplicitlyLeasableAccessoryTypeCriterion(
    _BawuPromptCriterion, ExplicitlyLeasableAccessoryTypeCriterion
):
    pass


class BawuFunctionalUnitWithBicycleCriterion(
    _BawuPromptCriterion, FunctionalUnitWithBicycleCriterion
):
    pass


class BawuSpecialRulesCriterion(_BawuPromptCriterion, SpecialRulesCriterion):
    pass
