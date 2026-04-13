import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Memoria(Base):
    __tablename__ = "memorias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    id_mem0: Mapped[str | None] = mapped_column(String(100), unique=True)
    conteudo: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(50), index=True)
    # Embedding dim 1536 — OpenAI text-embedding-3-small
    embedding = mapped_column(Vector(1536), nullable=True)
    metadados: Mapped[dict | None] = mapped_column(JSONB)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    usuario: Mapped["Usuario"] = relationship(back_populates="memorias")  # noqa: F821


class Pessoa(Base):
    __tablename__ = "pessoas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    cod_pessoa: Mapped[int] = mapped_column(Integer, unique=True, server_default="nextval('pessoas_cod_pessoa_seq')")
    nome: Mapped[str] = mapped_column(String(200))
    relacao: Mapped[str | None] = mapped_column(String(100))
    notas: Mapped[str | None] = mapped_column(Text)
    metadados: Mapped[dict | None] = mapped_column(JSONB)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    usuario: Mapped["Usuario"] = relationship(back_populates="pessoas")  # noqa: F821
