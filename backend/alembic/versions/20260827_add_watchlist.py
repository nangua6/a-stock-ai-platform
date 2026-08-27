"""add watchlist table

Revision ID: 20260827_001
Revises: 20260826_001
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "20260827_001"
down_revision: Union[str, None] = "20260826_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"])
    op.create_index("ix_watchlist_items_symbol", "watchlist_items", ["symbol"])
    op.create_unique_constraint("uq_watchlist_user_symbol", "watchlist_items", ["user_id", "symbol"])


def downgrade() -> None:
    op.drop_table("watchlist_items")
