"""Repository used when validation results must not be stored."""

from app.domain.validation_results import ValidationReport


class NoOpValidationReportRepository:
    """Accept reports without persisting them."""

    async def save(self, report: ValidationReport) -> None:
        return None
