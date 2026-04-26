import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
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

    # WhatsApp Modo 1 — opt-in por pessoa (whitelist)
    # Numero formato internacional sem +/espacos: "5588981504634"
    numero_whatsapp: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    flg_monitorar_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    usuario: Mapped["Usuario"] = relationship(back_populates="pessoas")  # noqa: F821


class Evento(Base):
    """
    Memoria episodica — o que aconteceu e quando.
    Diferente de Memoria (fato atemporal), Evento tem dat_ocorreu e e sempre pontual.
    Exemplos: "visitei loja X", "reuniao com fornecedor Y", "resolvi problema Z".
    """
    __tablename__ = "eventos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # Quando o evento aconteceu (nao quando foi registrado)
    dat_ocorreu: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    resumo: Mapped[str] = mapped_column(Text)
    # Categorias: visita_loja, reuniao, decisao, problema, conquista, deslocamento, saude, outro
    categoria: Mapped[str] = mapped_column(String(50), index=True)
    # Lojas mencionadas — texto livre por enquanto (ex: ["Salgueiro", "Petrolina"])
    lojas: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)))
    # IDs de pessoas envolvidas — FK soft (nao enforcement)
    pessoas_envolvidas: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    embedding = mapped_column(Vector(1536), nullable=True)
    metadados: Mapped[dict | None] = mapped_column(JSONB)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="eventos")  # noqa: F821
