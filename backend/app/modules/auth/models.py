import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cod_usuario: Mapped[int] = mapped_column(Integer, unique=True, server_default="nextval('usuarios_cod_usuario_seq')")
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    conversas: Mapped[list["Conversa"]] = relationship(back_populates="usuario")  # noqa: F821
    memorias: Mapped[list["Memoria"]] = relationship(back_populates="usuario")  # noqa: F821
    pessoas: Mapped[list["Pessoa"]] = relationship(back_populates="usuario")  # noqa: F821
    eventos: Mapped[list["Evento"]] = relationship(back_populates="usuario")  # noqa: F821
