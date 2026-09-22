import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.adapters.llm import ChatConfig, LLMClient
from app.domain.criterion import CriterionAnswer, CriterionResult, SpecialRuleResult
from app.domain.validation import (
    ValidationRequest,
)
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformation,
)

DEFAULT_MODELS = ("gpt-luna", "glm-5.3")

EXPLICITLY_NOT_LEASABLE_PROMPT_PATH = (
    Path(__file__).with_name("prompts") / "explicitly_not_leasable_type.md"
)

EXPLICITLY_LEASABLE_PROMPT_PATH = (
    Path(__file__).with_name("prompts") / "explicitly_leasable_type.md"
)

TECHNICAL_BICYCLE_COMPONENT_PROMPT_PATH = (
    Path(__file__).with_name("prompts") / "technical_bicycle_component.md"
)

STVZO_EQUIPMENT_PROMPT_PATH = Path(__file__).with_name("prompts") / "stvzo_equipment.md"

FUNCTIONAL_UNIT_WITH_BICYCLE_PROMPT_PATH = (
    Path(__file__).with_name("prompts") / "functional_unit_with_bicycle.md"
)

PERMANENTLY_MOUNTED_PROMPT_PATH = (
    Path(__file__).with_name("prompts") / "permanently_mounted.md"
)

SPECIAL_RULES_PROMPT_PATH = Path(__file__).with_name("prompts") / "special_rules.md"


class _CriterionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    answer: CriterionAnswer
    details: str = Field(min_length=1)


class _SpecialRulesResponse(_CriterionResponse):
    leasable: CriterionAnswer

    @model_validator(mode="after")
    def validate_leasable_matches_answer(self) -> "_SpecialRulesResponse":
        if self.answer is CriterionAnswer.YES:
            if self.leasable is CriterionAnswer.UNKNOWN:
                raise ValueError(
                    "leasable must be YES or NO when a special rule matches"
                )
        elif self.leasable is not CriterionAnswer.UNKNOWN:
            raise ValueError(
                "leasable must be UNKNOWN when no definitive special rule matches"
            )
        return self


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


def load_prompt(path: Path, response_model: type[BaseModel]) -> str:
    """Load criterion instructions and append their response contract."""
    prompt = path.read_text(encoding="utf-8").strip()
    schema = json.dumps(
        response_model.model_json_schema(), ensure_ascii=False, indent=2
    )
    return (
        f"{prompt}\n\n"
        "# Output\n\n"
        "Return exactly one JSON object and no surrounding text. "
        "The object must match this JSON Schema:\n\n"
        f"```json\n{schema}\n```"
    )


def _product_prompt(
    request: ValidationRequest,
    product_information: AccessoryProductInformation,
) -> str:
    product = request.product
    return json.dumps(
        {
            "brand": product.brand,
            "model": product.model,
            "product_information": {
                "summary": product_information.summary,
                "sources": [
                    {"title": source.title, "url": source.url}
                    for source in product_information.sources
                ],
            },
        },
        ensure_ascii=False,
    )


async def _generate_structured_response(
    llm_client: LLMClient,
    request: ValidationRequest,
    product_information: AccessoryProductInformation,
    prompt_path: Path,
    response_model: type[ResponseModel],
    config: ChatConfig | None,
) -> ResponseModel:
    selected_config = config or llm_client.config.with_overrides(models=DEFAULT_MODELS)
    response = await llm_client.generate(
        _product_prompt(request, product_information),
        instructions=load_prompt(prompt_path, response_model),
        config=selected_config,
    )
    try:
        return response_model.model_validate_json(response.text)
    except ValidationError:
        raise ValueError("LLM returned an invalid criterion response") from None


class ExplicitlyNotLeasableAccessoryTypeCriterion:
    id = "explicitly_not_leasable_type"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            EXPLICITLY_NOT_LEASABLE_PROMPT_PATH,
            _CriterionResponse,
            config,
        )
        return CriterionResult(result.answer, result.details)


class ExplicitlyLeasableAccessoryTypeCriterion:
    id = "explicitly_leasable_type"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            EXPLICITLY_LEASABLE_PROMPT_PATH,
            _CriterionResponse,
            config,
        )
        return CriterionResult(result.answer, result.details)


class TechnicalBicycleComponentCriterion:
    id = "technical_bicycle_component"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            TECHNICAL_BICYCLE_COMPONENT_PROMPT_PATH,
            _CriterionResponse,
            config,
        )
        return CriterionResult(result.answer, result.details)


class StvzoEquipmentCriterion:
    id = "stvzo_equipment"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            STVZO_EQUIPMENT_PROMPT_PATH,
            _CriterionResponse,
            config,
        )
        return CriterionResult(result.answer, result.details)


class FunctionalUnitWithBicycleCriterion:
    id = "functional_unit_with_bicycle"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            FUNCTIONAL_UNIT_WITH_BICYCLE_PROMPT_PATH,
            _CriterionResponse,
            config,
        )
        return CriterionResult(result.answer, result.details)


class PermanentlyMountedCriterion:
    id = "permanently_mounted"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            PERMANENTLY_MOUNTED_PROMPT_PATH,
            _CriterionResponse,
            config,
        )
        return CriterionResult(result.answer, result.details)


class SpecialRulesCriterion:
    id = "special_rules"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        config: ChatConfig | None = None,
    ) -> SpecialRuleResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            SPECIAL_RULES_PROMPT_PATH,
            _SpecialRulesResponse,
            config,
        )
        return SpecialRuleResult(result.answer, result.leasable, result.details)
