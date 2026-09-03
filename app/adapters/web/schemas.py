from pydantic import BaseModel, ConfigDict, Field


class ClassificationContextWebRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(default="default", min_length=1, max_length=100)
    employee_type: str | None = Field(default=None, max_length=100)


class AccessoryClassificationWebRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    accessory_name: str = Field(min_length=1, max_length=300)
    context: ClassificationContextWebRequest = Field(
        default_factory=ClassificationContextWebRequest
    )


class AccessoryClassificationWebResponse(BaseModel):
    accessory_name: str
    is_leasable: bool
    description: str | None = None
    evaluated_rules: dict[str, bool] = Field(default_factory=dict)


class ErrorWebResponse(BaseModel):
    code: str
    message: str
    details: str | None = None


class ErrorListWebResponse(BaseModel):
    errors: list[ErrorWebResponse]
