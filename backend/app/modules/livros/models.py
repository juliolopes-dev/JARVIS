import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Livro(Base):
    __tablename__ = "livros"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)

    titulo: Mapped[str] = mapped_column(String(300))
    autor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    total_paginas: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    dat_upload: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunks: Mapped[list["LivroChunk"]] = relationship(
        back_populates="livro", order_by="LivroChunk.numero", cascade="all, delete-orphan"
    )
    progresso: Mapped["LeituraProgresso | None"] = relationship(
        back_populates="livro", cascade="all, delete-orphan", uselist=False
    )


class LivroChunk(Base):
    __tablename__ = "livro_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_livro: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("livros.id", ondelete="CASCADE"), index=True
    )

    numero: Mapped[int] = mapped_column(Integer, index=True)       # posicao global (1-based)
    capitulo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    conteudo: Mapped[str] = mapped_column(Text)
    total_palavras: Mapped[int] = mapped_column(Integer, default=0)

    livro: Mapped["Livro"] = relationship(back_populates="chunks")


class LeituraProgresso(Base):
    __tablename__ = "leitura_progresso"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_livro: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("livros.id", ondelete="CASCADE"), index=True, unique=True
    )

    chunk_atual: Mapped[int] = mapped_column(Integer, default=1)   # proximo chunk a ler
    tamanho_chunk: Mapped[int] = mapped_column(Integer, default=300)  # palavras por chunk
    flg_modo_estudo: Mapped[bool] = mapped_column(Boolean, default=False)
    flg_concluido: Mapped[bool] = mapped_column(Boolean, default=False)

    dat_ultimo_acesso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dat_conclusao: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    livro: Mapped["Livro"] = relationship(back_populates="progresso")
