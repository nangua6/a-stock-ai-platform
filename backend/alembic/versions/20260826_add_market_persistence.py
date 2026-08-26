"""add market persistence models

Revision ID: 20260826_001
Revises: 
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "20260826_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### New tables added by this migration ###
    # Note: This is the initial migration. Tables that already exist in the
    # database (users, accounts, stocks, klines, orders, trades, positions,
    # signals) are created via Base.metadata.create_all in dev mode.
    # This migration adds the three new persistence tables.

    # -- data_sync_jobs --
    op.create_table(
        "data_sync_jobs",
        sa.Column("job_id", sa.String(50), nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("data_timestamp", sa.String(30), nullable=True),
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_data_sync_jobs_job_id", "data_sync_jobs", ["job_id"], unique=True)
    op.create_index("ix_data_sync_jobs_job_type", "data_sync_jobs", ["job_type"])
    op.create_index("ix_data_sync_jobs_symbol", "data_sync_jobs", ["symbol"])

    # -- technical_snapshots --
    op.create_table(
        "technical_snapshots",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.String(10), nullable=False),
        sa.Column("ma5", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ma10", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ma20", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ma60", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ema12", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ema26", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("macd_line", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("macd_signal", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("macd_histogram", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rsi", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("kdj_k", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("kdj_d", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("kdj_j", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("boll_upper", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("boll_middle", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("boll_lower", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("atr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("volume_ma5", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("volume_ma10", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("volume_ma20", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("volatility", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("turnover_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("amplitude", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("period", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_source", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_technical_snapshots_symbol", "technical_snapshots", ["symbol"])
    op.create_index("ix_technical_snapshots_trade_date", "technical_snapshots", ["trade_date"])

    # -- analysis_snapshots --
    op.create_table(
        "analysis_snapshots",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False, server_default=""),
        sa.Column("trade_date", sa.String(10), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("change_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("volume", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("technical_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("fundamental_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recommendation", sa.String(20), nullable=False, server_default="DATA_UNAVAILABLE"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("technical_detail", sa.JSON(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("risk_details", sa.JSON(), nullable=True),
        sa.Column("bull_case", sa.Text(), nullable=True),
        sa.Column("bear_case", sa.Text(), nullable=True),
        sa.Column("key_risks", sa.JSON(), nullable=True),
        sa.Column("data_quality", sa.String(20), nullable=False, server_default="GOOD"),
        sa.Column("data_source", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analysis_snapshots_symbol", "analysis_snapshots", ["symbol"])
    op.create_index("ix_analysis_snapshots_trade_date", "analysis_snapshots", ["trade_date"])

    # -- Add unique constraint to klines if not exists --
    # The klines table should already have this constraint from the model,
    # but we add it here explicitly for migration completeness.
    try:
        op.create_unique_constraint(
            "uq_kline_symbol_date_tf", "klines",
            ["symbol", "trade_date", "timeframe"],
        )
    except Exception:
        pass  # Constraint may already exist


def downgrade() -> None:
    op.drop_table("analysis_snapshots")
    op.drop_table("technical_snapshots")
    op.drop_table("data_sync_jobs")
    try:
        op.drop_constraint("uq_kline_symbol_date_tf", "klines")
    except Exception:
        pass
