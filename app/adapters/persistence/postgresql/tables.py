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

product = Table(
    "product",
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
    Column("validation_status", String(32), nullable=False),
    Column("leasability_validation_status", String(32)),
)
Index("ix_product_origin", product.c.source, product.c.external_ref)

validation_execution = Table(
    "validation_execution",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("product.id"), nullable=False),
    Column("position", Integer, nullable=False),
    Column("validation_id", Text, nullable=False),
    Column("executed_at", DateTime(timezone=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("details", Text, nullable=False),
    UniqueConstraint("product_id", "position"),
    UniqueConstraint("product_id", "validation_id"),
)

llm_request = Table(
    "llm_request",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    # Not a foreign key: requests are written before the product is committed,
    # and failed validations have requests but no persisted product.
    Column("product_id", UUID(as_uuid=True), index=True),
    Column("validation_id", Text),
    Column("description", Text),
    Column("prompt", Text, nullable=False),
    Column("instructions", Text, nullable=False),
    Column("instructions_hash", String(64), nullable=False),
    Column("requested_models", JSONB, nullable=False),
    Column("tools", JSONB, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("response", JSONB),
    Column("input_tokens", Integer),
    Column("output_tokens", Integer),
    Column("total_tokens", Integer),
    Column("error", Text),
)
