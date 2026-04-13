import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Time, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id"), unique=True, index=True
    )
    modelo_preferido: Mapped[str] = mapped_column(
        String(50), default="claude-sonnet-4-6"
    )
    tema: Mapped[str] = mapped_column(String(20), default="escuro")
    voz_resposta: Mapped[str | None] = mapped_column(String(100))
    flg_briefing_diario: Mapped[bool] = mapped_column(Boolean, default=True)
    horario_briefing: Mapped[time] = mapped_column(Time, default=time(8, 0))
    flg_notificacoes: Mapped[bool] = mapped_column(Boolean, default=True)
    preferencias: Mapped[dict | None] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
