"""PostgreSQL tables for submitted products, validation histories, and LLM requests."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

products = Table(
    "products",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("source", Text, nullable=False),
    Column("external_ref", Text, nullable=False),
    Column("product_type", String(32), nullable=False),
    Column("brand", Text, nullable=False),
    Column("model", Text, nullable=False),
    Column("year", Integer),
    Column("size", Text),
    Column("color", Text),
    Column("price", Numeric),
    Column("category", Text),
    Column("report_status", String(32), nullable=False),
)
Index("ix_products_origin", products.c.source, products.c.external_ref)

validation_executions = Table(
    "validation_executions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("products.id"), nullable=False),
    Column("position", Integer, nullable=False),
    Column("validation_id", Text, nullable=False),
    Column("executed_at", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("details", Text, nullable=False),
    UniqueConstraint("product_id", "position"),
    UniqueConstraint("product_id", "validation_id"),
)

llm_requests = Table(
    "llm_requests",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    # Requests are written during validation, before its execution is committed.
    # Failed validations also have requests but no persisted execution.
    Column("validation_execution_id", UUID(as_uuid=True), index=True),
    Column("prompt", Text, nullable=False),
    Column("instructions", Text, nullable=False),
    Column("instructions_hash", String(64), nullable=False),
    Column("requested_models", JSONB, nullable=False),
    Column("tools", JSONB, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("response", JSONB),
    Column("error", Text),
)
