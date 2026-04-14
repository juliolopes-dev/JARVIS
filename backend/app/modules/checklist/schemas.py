import uuid
from datetime import datetime

from pydantic import BaseModel


# ─── Lista ────────────────────────────────────────────────────────────────────

class ListaCreate(BaseModel):
    nome: str
    cor: str = "#3b82f6"
    icone: str = "list"
    ordem: int = 0


class ListaUpdate(BaseModel):
    nome: str | None = None
    cor: str | None = None
    icone: str | None = None
    ordem: int | None = None


class ListaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    nome: str
    cor: str
    icone: str
    ordem: int
    criado_em: datetime
    total_tarefas: int = 0
    total_concluidas: int = 0


# ─── Tarefa ───────────────────────────────────────────────────────────────────

class TarefaCreate(BaseModel):
    titulo: str
    descricao: str | None = None
    id_lista: uuid.UUID | None = None
    prioridade: str = "media"  # baixa, media, alta, urgente
    dat_vencimento: datetime | None = None
    ordem: int = 0


class TarefaUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    id_lista: uuid.UUID | None = None
    prioridade: str | None = None  # baixa, media, alta, urgente
    dat_vencimento: datetime | None = None
    ordem: int | None = None


class TarefaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    id_lista: uuid.UUID | None
    titulo: str
    descricao: str | None
    prioridade: str
    dat_vencimento: datetime | None
    flg_concluida: bool
    dat_concluida: datetime | None
    ordem: int
    criado_em: datetime
    atualizado_em: datetime
