import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SubscricaoPush(Base):
    __tablename__ = "subscricoes_push"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    endpoint: Mapped[str] = mapped_column(Text)
    chave_p256dh: Mapped[str] = mapped_column(Text)
    chave_auth: Mapped[str] = mapped_column(Text)
    dispositivo: Mapped[str | None] = mapped_column(String(100))
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
