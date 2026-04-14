import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lista(Base):
    __tablename__ = "listas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)

    nome: Mapped[str] = mapped_column(String(100))
    cor: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    icone: Mapped[str] = mapped_column(String(50), default="list")
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tarefas: Mapped[list["Tarefa"]] = relationship(
        back_populates="lista", order_by="Tarefa.ordem"
    )


class Tarefa(Base):
    __tablename__ = "tarefas_checklist"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    id_lista: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("listas.id"), index=True, nullable=True
    )

    titulo: Mapped[str] = mapped_column(String(300))
    descricao: Mapped[str | None] = mapped_column(Text)

    # Prioridade: baixa, media, alta, urgente
    prioridade: Mapped[str] = mapped_column(String(20), default="media", index=True)

    # Vencimento opcional
    dat_vencimento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Conclusao
    flg_concluida: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    dat_concluida: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    ordem: Mapped[int] = mapped_column(Integer, default=0)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lista: Mapped["Lista | None"] = relationship(back_populates="tarefas")
