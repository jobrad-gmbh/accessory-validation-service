"""Create validation history and LLM requests tables.

Revision ID: 0001_validation_history
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_validation_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=False),
        sa.Column("product_type", sa.String(32), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer()),
        sa.Column("size", sa.Text()),
        sa.Column("color", sa.Text()),
        sa.Column("price", sa.Numeric()),
        sa.Column("category", sa.Text()),
        sa.Column("report_status", sa.String(32), nullable=False),
    )
    op.create_index("ix_products_origin", "products", ["source", "external_ref"])
    op.create_table(
        "validation_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("validation_id", sa.Text(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.UniqueConstraint("product_id", "position"),
        sa.UniqueConstraint("product_id", "validation_id"),
    )
    op.create_table(
        "llm_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("validation_execution_id", postgresql.UUID(as_uuid=True)),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("instructions_hash", sa.String(64), nullable=False),
        sa.Column("requested_models", postgresql.JSONB(), nullable=False),
        sa.Column("tools", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
    )
    op.create_index(
        "ix_llm_requests_validation_execution_id", "llm_requests", ["validation_execution_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_llm_requests_validation_execution_id", table_name="llm_requests")
    op.drop_table("llm_requests")
    op.drop_table("validation_executions")
    op.drop_index("ix_products_origin", table_name="products")
    op.drop_table("products")
