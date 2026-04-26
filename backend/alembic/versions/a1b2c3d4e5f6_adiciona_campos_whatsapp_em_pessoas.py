"""adiciona campos whatsapp em pessoas

Revision ID: a1b2c3d4e5f6
Revises: dffb7c84dba5
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dffb7c84dba5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona suporte a WhatsApp Modo 1 (Observador) — opt-in por pessoa (whitelist)
    op.add_column(
        "pessoas",
        sa.Column("numero_whatsapp", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "pessoas",
        sa.Column(
            "flg_monitorar_whatsapp",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_unique_constraint(
        "uq_pessoas_numero_whatsapp", "pessoas", ["numero_whatsapp"]
    )
    op.create_index(
        "ix_pessoas_numero_whatsapp", "pessoas", ["numero_whatsapp"]
    )


def downgrade() -> None:
    op.drop_index("ix_pessoas_numero_whatsapp", table_name="pessoas")
    op.drop_constraint("uq_pessoas_numero_whatsapp", "pessoas", type_="unique")
    op.drop_column("pessoas", "flg_monitorar_whatsapp")
    op.drop_column("pessoas", "numero_whatsapp")
