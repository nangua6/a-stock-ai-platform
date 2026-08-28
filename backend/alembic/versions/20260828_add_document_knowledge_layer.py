"""add document knowledge layer

Revision ID: doc_layer_001
Revises: 20260827_add_watchlist
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'doc_layer_001'
down_revision = '20260827_add_watchlist'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_type enum
    document_type_enum = postgresql.ENUM(
        'FINANCIAL', 'NEWS', 'ANNOUNCEMENT',
        name='document_type_enum',
        create_type=False,
    )
    document_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'documents',
        sa.Column('id', sa.String(64), primary_key=True, comment='Internal UUID'),
        sa.Column('document_id', sa.String(128), unique=True, nullable=False, index=True,
                  comment='Stable document ID'),
        sa.Column('document_type', sa.Enum('FINANCIAL', 'NEWS', 'ANNOUNCEMENT',
                                           name='document_type_enum', create_type=False),
                  nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.Text, nullable=False, server_default=''),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('url', sa.Text, nullable=True),
        sa.Column('published_at', sa.String(30), nullable=True, index=True),
        sa.Column('retrieved_at', sa.String(30), nullable=True),
        sa.Column('report_period', sa.String(20), nullable=True),
        sa.Column('metadata_json', sa.Text, nullable=True),
        sa.Column('generated_from_structured_data', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('content_hash', sa.String(64), nullable=False, index=True),
        sa.Column('data_quality', sa.String(20), nullable=False, server_default='UNKNOWN'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now(), nullable=False),
        comment='Unified document knowledge base',
    )

    # Composite indexes
    op.create_index('ix_documents_symbol_type', 'documents', ['symbol', 'document_type'])
    op.create_index('ix_documents_symbol_published', 'documents', ['symbol', 'published_at'])


def downgrade() -> None:
    op.drop_table('documents')
    op.execute('DROP TYPE IF EXISTS document_type_enum')
