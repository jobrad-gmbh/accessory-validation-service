import json
import re
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.adapters.llm import (
    LLMClient,
    LLMModelSettings,
    LLMRequestSpec,
    LLMResponseError,
    summarize_validation_error,
)
from app.domain.criterion import CriterionAnswer, CriterionResult
from app.domain.validation import (
    ValidationRequest,
)
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformation,
)

DEFAULT_MODELS = ("gpt-6-luna", "glm-5.3")

LeasabilityCriterionId = Literal[
    "explicitly_not_leasable_type",
    "explicitly_leasable_type",
    "technical_bicycle_component",
    "stvzo_equipment",
    "functional_unit_with_bicycle",
    "permanently_mounted",
    "special_rules",
]

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


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)

_JSON_CODE_FENCE = re.compile(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL | re.IGNORECASE)


def load_prompt(path: Path, response_model: type[BaseModel]) -> str:
    """Load criterion instructions and append their response contract."""
    prompt = path.read_text(encoding="utf-8").strip()
    schema = json.dumps(
        response_model.model_json_schema(), ensure_ascii=False, indent=2
    )
    return (
        f"{prompt}\n\n"
        "# Output\n\n"
        "Return exactly one JSON object and no surrounding text. No json fences. "
        "Nothing can wrap the JSON object. The JSON object must be valid and parseable. "
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
            "price_eur": str(product.price) if product.price is not None else None,
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
    settings: LLMModelSettings | None,
    description: str | None = None,
    validation_id: str | None = None,
) -> ResponseModel:
    config = llm_client.config.with_overrides(models=DEFAULT_MODELS, reasoning_effort="xhigh")
    if settings is not None:
        config = config.with_settings(settings)
    response = await llm_client.generate(
        LLMRequestSpec(
            prompt=_product_prompt(request, product_information),
            instructions=load_prompt(prompt_path, response_model),
            description=description,
            config=config,
            product_id=request.product.id,
            validation_id=validation_id,
        )
    )
    text = response.text.strip()
    fence = _JSON_CODE_FENCE.fullmatch(text)
    if fence is not None:
        text = fence.group(1).strip()
    try:
        return response_model.model_validate_json(text)
    except ValidationError as error:
        raise LLMResponseError(
            f"Model '{response.model}' returned an invalid criterion response"
            f" during '{description}': {summarize_validation_error(error)}"
        ) from error


class ExplicitlyNotLeasableAccessoryTypeCriterion:
    id = "explicitly_not_leasable_type"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            EXPLICITLY_NOT_LEASABLE_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class ExplicitlyLeasableAccessoryTypeCriterion:
    id = "explicitly_leasable_type"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            EXPLICITLY_LEASABLE_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class TechnicalBicycleComponentCriterion:
    id = "technical_bicycle_component"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            TECHNICAL_BICYCLE_COMPONENT_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class StvzoEquipmentCriterion:
    id = "stvzo_equipment"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            STVZO_EQUIPMENT_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class FunctionalUnitWithBicycleCriterion:
    id = "functional_unit_with_bicycle"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            FUNCTIONAL_UNIT_WITH_BICYCLE_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class PermanentlyMountedCriterion:
    id = "permanently_mounted"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            PERMANENTLY_MOUNTED_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)


class SpecialRulesCriterion:
    id = "special_rules"

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult:
        result = await _generate_structured_response(
            self._llm_client,
            request,
            product_information,
            SPECIAL_RULES_PROMPT_PATH,
            _CriterionResponse,
            settings,
            self.id,
            validation_id,
        )
        return CriterionResult(result.answer, result.details, self.id)
