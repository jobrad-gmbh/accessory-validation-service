"""TypeSafe's typed evaluation API; it does not expose text generation or streaming."""

import asyncio
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError
from pydantic_settings import SettingsConfigDict

from app.adapters.llm.config import LLMConfig
from app.adapters.llm.errors import (
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    ModelsNotFoundError,
)

State = str | dict[str, JsonValue] | list[JsonValue]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class JevConfig(LLMConfig):
    model_config = SettingsConfigDict(env_prefix="TYPESAFE_")


class _TypedModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)


class NoulQuestion(_TypedModel):
    type: Literal["noul"] = "noul"
    instructions: State
    criteria: dict[Literal["true", "false"], str] | None = None


class ChoiceQuestion(_TypedModel):
    type: Literal["choice"] = "choice"
    instructions: State
    criteria: dict[str, str | None] = Field(min_length=1)


class ScoreQuestion(_TypedModel):
    type: Literal["score"] = "score"
    instructions: State
    criteria: list[str] = Field(min_length=2)


Question = Annotated[
    NoulQuestion | ChoiceQuestion | ScoreQuestion, Field(discriminator="type")
]


class JevRequest(_TypedModel):
    state: State
    questions: dict[str, Question] = Field(min_length=1)


class NoulAnswer(_TypedModel):
    type: Literal["noul"]
    noul: Probability


class ChoiceAnswer(_TypedModel):
    type: Literal["choice"]
    choice: str
    probabilities: dict[str, Probability]
    confidence: Probability


class ScoreAnswer(_TypedModel):
    type: Literal["score"]
    score: float = Field(ge=0, allow_inf_nan=False)
    legend: dict[str, str]
    probabilities: dict[str, Probability]
    confidence: Probability


Answer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class JevResponse(_TypedModel):
    model: str
    answers: dict[str, Answer]


class JevClient:
    def __init__(
        self, http_client: httpx.AsyncClient, config: JevConfig | None = None
    ) -> None:
        self._http = http_client
        self.config = config if config is not None else JevConfig.from_env()

    async def evaluate(
        self,
        request: JevRequest,
        *,
        config: JevConfig | None = None,
    ) -> JevResponse:
        selected = config if config is not None else self.config
        headers = {"Accept": "application/json"}
        if selected.api_key is not None:
            headers["Authorization"] = f"Bearer {selected.api_key.get_secret_value()}"
        for model in selected.models:
            try:
                async with asyncio.timeout(selected.timeout_seconds):
                    response = await self._http.post(
                        f"{str(selected.base_url).rstrip('/')}/systemone",
                        json={
                            **request.model_dump(mode="json", exclude_none=True),
                            "model": model,
                        },
                        headers=headers,
                        timeout=selected.timeout_seconds,
                        follow_redirects=False,
                    )
            except (TimeoutError, httpx.TimeoutException):
                raise LLMTimeoutError("Jev request timed out") from None
            except httpx.RequestError:
                raise LLMError("Could not reach the Jev service") from None
            if not response.is_success:
                # The public docs do not specify a missing-model error format.
                # Accept an explicit code, never guess from a generic 404/422.
                try:
                    body = response.json()
                except ValueError:
                    body = None
                error = body.get("error") if isinstance(body, dict) else None
                if (
                    response.status_code in (400, 404, 422)
                    and isinstance(error, dict)
                    and error.get("code") == "model_not_found"
                ):
                    continue
                raise LLMError(
                    f"Jev service returned HTTP {response.status_code}",
                    status_code=response.status_code,
                )
            try:
                result = JevResponse.model_validate_json(response.content)
            except ValidationError:
                raise LLMResponseError("Invalid Jev response") from None
            self._validate_answers(request, result)
            return result
        raise ModelsNotFoundError(selected.models)

    @staticmethod
    def _validate_answers(request: JevRequest, result: JevResponse) -> None:
        if result.answers.keys() != request.questions.keys():
            raise LLMResponseError("Jev answers do not match the requested questions")
        for key, question in request.questions.items():
            answer = result.answers[key]
            if answer.type != question.type:
                raise LLMResponseError("Jev returned an incorrect answer type")
            if isinstance(answer, ChoiceAnswer) and isinstance(
                question, ChoiceQuestion
            ):
                if (
                    answer.choice not in question.criteria
                    or answer.probabilities.keys() != question.criteria.keys()
                ):
                    raise LLMResponseError("Jev returned an unknown choice")
            if isinstance(answer, ScoreAnswer) and isinstance(question, ScoreQuestion):
                legend = {str(i): level for i, level in enumerate(question.criteria)}
                if (
                    answer.legend != legend
                    or answer.probabilities.keys() != legend.keys()
                    or answer.score > len(legend) - 1
                ):
                    raise LLMResponseError("Jev returned an invalid score")
            if isinstance(answer, (ChoiceAnswer, ScoreAnswer)):
                if abs(sum(answer.probabilities.values()) - 1) > 0.01:
                    raise LLMResponseError(
                        "Jev returned an invalid probability distribution"
                    )
