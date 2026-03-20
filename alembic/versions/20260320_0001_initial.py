"""initial schema

Revision ID: 20260320_0001
Revises:
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("prompt_preview", sa.String(length=160), nullable=False),
        sa.Column("evidence_strength", sa.Float(), nullable=False),
        sa.Column("sensitivity", sa.String(length=30), nullable=False),
        sa.Column("requested_action", sa.String(length=100), nullable=True),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("reason_summary", sa.Text(), nullable=False),
        sa.Column("suggested_response", sa.Text(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_requests_id", "requests", ["id"])
    op.create_index("ix_requests_role", "requests", ["role"])
    op.create_index("ix_requests_outcome", "requests", ["outcome"])
    op.create_index("ix_requests_sensitivity", "requests", ["sensitivity"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("requests.id"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])

    op.create_table(
        "review_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("requests.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reviewer", sa.String(length=100), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_items_status", "review_items", ["status"])
    op.create_index("ix_review_items_request_id", "review_items", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_review_items_request_id", table_name="review_items")
    op.drop_index("ix_review_items_status", table_name="review_items")
    op.drop_table("review_items")
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_requests_sensitivity", table_name="requests")
    op.drop_index("ix_requests_outcome", table_name="requests")
    op.drop_index("ix_requests_role", table_name="requests")
    op.drop_index("ix_requests_id", table_name="requests")
    op.drop_table("requests")
