"""adiciona historico_notificacoes

Revision ID: b1d20c661108
Revises: f22aa210c728
Create Date: 2026-04-13 21:55:25.230564

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1d20c661108'
down_revision: Union[str, None] = 'f22aa210c728'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('historico_notificacoes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('id_usuario', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=30), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('corpo', sa.Text(), nullable=True),
    sa.Column('flg_lida', sa.Boolean(), nullable=False),
    sa.Column('dat_lida', sa.DateTime(timezone=True), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_historico_notificacoes_criado_em'), 'historico_notificacoes', ['criado_em'], unique=False)
    op.create_index(op.f('ix_historico_notificacoes_flg_lida'), 'historico_notificacoes', ['flg_lida'], unique=False)
    op.create_index(op.f('ix_historico_notificacoes_id_usuario'), 'historico_notificacoes', ['id_usuario'], unique=False)
    op.create_index(op.f('ix_historico_notificacoes_tipo'), 'historico_notificacoes', ['tipo'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_historico_notificacoes_tipo'), table_name='historico_notificacoes')
    op.drop_index(op.f('ix_historico_notificacoes_id_usuario'), table_name='historico_notificacoes')
    op.drop_index(op.f('ix_historico_notificacoes_flg_lida'), table_name='historico_notificacoes')
    op.drop_index(op.f('ix_historico_notificacoes_criado_em'), table_name='historico_notificacoes')
    op.drop_table('historico_notificacoes')
