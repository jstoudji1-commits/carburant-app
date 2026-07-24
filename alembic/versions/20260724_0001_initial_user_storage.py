"""initial user storage

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260724_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_accounts",
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("password", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("email_verification_hash", sa.String(length=128), nullable=True),
        sa.Column("email_verification_expires_at", sa.String(length=40), nullable=True),
        sa.Column("password_reset_hash", sa.String(length=128), nullable=True),
        sa.Column("password_reset_expires_at", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("email"),
    )
    op.create_table(
        "landing_testers",
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.Column("ip", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("email"),
    )
    op.create_table(
        "station_overrides",
        sa.Column("station_id", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("station_id"),
    )
    op.create_table(
        "app_kv_store",
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade():
    op.drop_table("app_kv_store")
    op.drop_table("station_overrides")
    op.drop_table("landing_testers")
    op.drop_table("user_accounts")
