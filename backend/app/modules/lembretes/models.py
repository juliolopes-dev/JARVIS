import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Lembrete(Base):
    __tablename__ = "lembretes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)

    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)

    # Data/hora do disparo
    dat_lembrete: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # ID do job no APScheduler (para cancelar/editar)
    id_job: Mapped[str | None] = mapped_column(String(100))

    # Status: pendente, disparado, cancelado
    sts_lembrete: Mapped[str] = mapped_column(String(20), default="pendente", index=True)

    # Soft delete
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
