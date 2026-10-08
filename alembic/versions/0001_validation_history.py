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
        "product",
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
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("leasability_validation_status", sa.String(32)),
    )
    op.create_index("ix_product_origin", "product", ["source", "external_ref"])
    op.create_table(
        "validation_execution",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product.id"),
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
        "llm_request",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True)),
        sa.Column("validation_id", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("instructions_hash", sa.String(64), nullable=False),
        sa.Column("requested_models", postgresql.JSONB(), nullable=False),
        sa.Column("tools", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response", postgresql.JSONB()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_llm_request_product_id", "llm_request", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_request_product_id", table_name="llm_request")
    op.drop_table("llm_request")
    op.drop_table("validation_execution")
    op.drop_index("ix_product_origin", table_name="product")
    op.drop_table("product")
