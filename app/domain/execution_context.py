"""Ambient identity of the validation execution currently running.

Adapters (for example the LLM request recorder) read it to associate their own
records with the validation execution without every caller passing it along.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

_current_validation_execution_id: ContextVar[UUID | None] = ContextVar(
    "current_validation_execution_id", default=None
)


def current_validation_execution_id() -> UUID | None:
    return _current_validation_execution_id.get()


@contextmanager
def validation_execution_scope(execution_id: UUID) -> Generator[None, None, None]:
    token = _current_validation_execution_id.set(execution_id)
    try:
        yield
    finally:
        _current_validation_execution_id.reset(token)
