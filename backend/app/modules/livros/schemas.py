import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ─── Livro ────────────────────────────────────────────────────────────────────

class LivroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    autor: str | None
    total_paginas: int
    total_chunks: int
    dat_upload: datetime
    progresso: "ProgressoResponse | None" = None


# ─── Chunk ────────────────────────────────────────────────────────────────────

class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    numero: int
    capitulo: str | None
    conteudo: str
    total_palavras: int


# ─── Progresso ────────────────────────────────────────────────────────────────

class ProgressoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_atual: int
    tamanho_chunk: int
    flg_modo_estudo: bool
    flg_concluido: bool
    dat_ultimo_acesso: datetime | None
    dat_conclusao: datetime | None


class ProgressoUpdate(BaseModel):
    tamanho_chunk: int | None = None
    flg_modo_estudo: bool | None = None


# ─── Leitura (trecho + metadata) ──────────────────────────────────────────────

class LeituraResponse(BaseModel):
    livro_id: uuid.UUID
    titulo_livro: str
    chunk: ChunkResponse
    chunk_atual: int
    total_chunks: int
    porcentagem: float
    capitulo_concluido: bool    # ultimo chunk do capitulo atual
    livro_concluido: bool
    resumo_capitulo: str | None = None   # preenchido quando capitulo_concluido=True e modo estudo
    perguntas_estudo: list[str] | None = None  # preenchido no modo estudo
