import uuid
from datetime import datetime

from pydantic import BaseModel


class MemoriaResponse(BaseModel):
    id: uuid.UUID
    conteudo: str
    categoria: str
    metadados: dict | None
    flg_ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class PessoaCreate(BaseModel):
    nome: str
    relacao: str | None = None
    notas: str | None = None
    metadados: dict | None = None


class PessoaUpdate(BaseModel):
    nome: str | None = None
    relacao: str | None = None
    notas: str | None = None
    metadados: dict | None = None


class PessoaResponse(BaseModel):
    id: uuid.UUID
    cod_pessoa: int
    nome: str
    relacao: str | None
    notas: str | None
    metadados: dict | None
    flg_ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}
