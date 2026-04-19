"""adiciona tabela eventos

Revision ID: dffb7c84dba5
Revises: e146f61fceae
Create Date: 2026-04-18 22:07:46.708585

"""
from typing import Sequence, Union

import pgvector.sqlalchemy
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dffb7c84dba5'
down_revision: Union[str, None] = 'e146f61fceae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'eventos',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('id_usuario', sa.Uuid(), nullable=False),
        sa.Column('dat_ocorreu', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resumo', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(length=50), nullable=False),
        sa.Column('lojas', sa.ARRAY(sa.String(length=100)), nullable=True),
        sa.Column('pessoas_envolvidas', sa.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column('metadados', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('flg_ativo', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_eventos_categoria'), 'eventos', ['categoria'], unique=False)
    op.create_index(op.f('ix_eventos_dat_ocorreu'), 'eventos', ['dat_ocorreu'], unique=False)
    op.create_index(op.f('ix_eventos_id_usuario'), 'eventos', ['id_usuario'], unique=False)
    # Indice HNSW para busca semantica no resumo do evento
    op.execute(
        "CREATE INDEX IF NOT EXISTS eventos_embedding_idx "
        "ON eventos USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS eventos_embedding_idx")
    op.drop_index(op.f('ix_eventos_id_usuario'), table_name='eventos')
    op.drop_index(op.f('ix_eventos_dat_ocorreu'), table_name='eventos')
    op.drop_index(op.f('ix_eventos_categoria'), table_name='eventos')
    op.drop_table('eventos')
