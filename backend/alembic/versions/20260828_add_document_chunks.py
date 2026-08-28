"""add document chunks

Revision ID: doc_chunks_001
Revises: doc_layer_001
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'doc_chunks_001'
down_revision = 'doc_layer_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(64), primary_key=True, comment='Internal UUID'),
        sa.Column('chunk_id', sa.String(128), unique=True, nullable=False, index=True,
                  comment='Stable chunk ID'),
        sa.Column('document_id', sa.String(128), nullable=False, index=True,
                  comment='FK to documents.document_id'),
        sa.Column('chunk_index', sa.Integer, nullable=False,
                  comment='0-based index within document'),
        sa.Column('content', sa.Text, nullable=False,
                  comment='Chunk text content'),
        sa.Column('chunk_hash', sa.String(64), nullable=False, index=True,
                  comment='sha256 of normalized content'),
        sa.Column('metadata_json', sa.Text, nullable=True,
                  comment='JSON metadata'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_chunk_doc_index'),
        comment='Deterministic document chunks for RAG',
    )
    op.create_index('ix_chunk_doc_id', 'document_chunks', ['document_id'])


def downgrade() -> None:
    op.drop_table('document_chunks')
