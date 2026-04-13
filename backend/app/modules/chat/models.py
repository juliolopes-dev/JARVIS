import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    titulo: Mapped[str | None] = mapped_column(String(200))
    flg_ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    usuario: Mapped["Usuario"] = relationship(back_populates="conversas")  # noqa: F821
    mensagens: Mapped[list["Mensagem"]] = relationship(
        back_populates="conversa", order_by="Mensagem.criado_em"
    )


class Mensagem(Base):
    __tablename__ = "mensagens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_conversa: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversas.id"), index=True
    )
    papel: Mapped[str] = mapped_column(String(20))  # 'user', 'assistant', 'system'
    conteudo: Mapped[str] = mapped_column(Text)
    modelo_usado: Mapped[str | None] = mapped_column(String(50))
    tokens_entrada: Mapped[int | None] = mapped_column(Integer)
    tokens_saida: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relacionamentos
    conversa: Mapped["Conversa"] = relationship(back_populates="mensagens")
