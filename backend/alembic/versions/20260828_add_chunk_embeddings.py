"""add chunk embeddings

Revision ID: chunk_emb_001
Revises: doc_chunks_001
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'chunk_emb_001'
down_revision = 'doc_chunks_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (optional, for future upgrade)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'chunk_embeddings',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('chunk_id', sa.String(128), nullable=False, index=True),
        sa.Column('document_id', sa.String(128), nullable=False, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('document_type', sa.String(30), nullable=False, index=True),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('dimension', sa.Integer, nullable=False),
        sa.Column('vector_json', sa.Text, nullable=False,
                  comment='Embedding vector as JSON array'),
        sa.Column('content_hash', sa.String(64), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('chunk_id', 'model', name='uq_chunk_model'),
        comment='Chunk embedding vectors for RAG retrieval',
    )
    op.create_index('ix_chunk_emb_chunk_id', 'chunk_embeddings', ['chunk_id'])
    op.create_index('ix_chunk_emb_doc_id', 'chunk_embeddings', ['document_id'])
    op.create_index('ix_chunk_emb_symbol', 'chunk_embeddings', ['symbol'])
    op.create_index('ix_chunk_emb_content_hash', 'chunk_embeddings', ['content_hash'])


def downgrade() -> None:
    op.drop_table('chunk_embeddings')
