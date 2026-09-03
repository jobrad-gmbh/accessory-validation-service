from pydantic import BaseModel, ConfigDict, Field


class ClassificationContext(BaseModel):
    """Information that can select a rule or decision variant."""

    is_bawu: bool


class AccessoryClassification(BaseModel):
    """Domain result returned by the classifier."""

    model_config = ConfigDict(frozen=True)

    accessory_name: str
    is_leasable: bool
    description: str | None = None
    evaluated_rules: dict[str, bool] = Field(default_factory=dict)
