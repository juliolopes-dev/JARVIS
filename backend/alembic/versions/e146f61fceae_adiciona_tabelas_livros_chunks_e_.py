"""adiciona tabelas livros chunks e leitura_progresso

Revision ID: e146f61fceae
Revises: b1d20c661108
Create Date: 2026-04-14 18:17:46.319695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e146f61fceae'
down_revision: Union[str, None] = 'b1d20c661108'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('livros',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_usuario', sa.Uuid(), nullable=False),
    sa.Column('titulo', sa.String(length=300), nullable=False),
    sa.Column('autor', sa.String(length=200), nullable=True),
    sa.Column('total_paginas', sa.Integer(), nullable=False),
    sa.Column('total_chunks', sa.Integer(), nullable=False),
    sa.Column('flg_ativo', sa.Boolean(), nullable=False),
    sa.Column('dat_upload', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_livros_id_usuario'), 'livros', ['id_usuario'], unique=False)

    op.create_table('leitura_progresso',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_livro', sa.Uuid(), nullable=False),
    sa.Column('chunk_atual', sa.Integer(), nullable=False),
    sa.Column('tamanho_chunk', sa.Integer(), nullable=False),
    sa.Column('flg_modo_estudo', sa.Boolean(), nullable=False),
    sa.Column('flg_concluido', sa.Boolean(), nullable=False),
    sa.Column('dat_ultimo_acesso', sa.DateTime(timezone=True), nullable=True),
    sa.Column('dat_conclusao', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['id_livro'], ['livros.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leitura_progresso_id_livro'), 'leitura_progresso', ['id_livro'], unique=True)

    op.create_table('livro_chunks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_livro', sa.Uuid(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('capitulo', sa.String(length=300), nullable=True),
    sa.Column('conteudo', sa.Text(), nullable=False),
    sa.Column('total_palavras', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_livro'], ['livros.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_livro_chunks_id_livro'), 'livro_chunks', ['id_livro'], unique=False)
    op.create_index(op.f('ix_livro_chunks_numero'), 'livro_chunks', ['numero'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_livro_chunks_numero'), table_name='livro_chunks')
    op.drop_index(op.f('ix_livro_chunks_id_livro'), table_name='livro_chunks')
    op.drop_table('livro_chunks')
    op.drop_index(op.f('ix_leitura_progresso_id_livro'), table_name='leitura_progresso')
    op.drop_table('leitura_progresso')
    op.drop_index(op.f('ix_livros_id_usuario'), table_name='livros')
    op.drop_table('livros')
