"""Persistence contract for complete product validation histories."""

from typing import Protocol

from app.domain.validation_results import ValidationReport


class ValidationReportRepository(Protocol):
    async def save(self, report: ValidationReport) -> None:
        """Atomically save the submitted product and all validation executions.

        This includes each execution's status, details, and criterion results.
        A storage error must propagate so callers do not receive an unsaved result.
        """
        ...
