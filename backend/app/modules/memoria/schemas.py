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
    numero_whatsapp: str | None = None
    flg_monitorar_whatsapp: bool = False


class PessoaUpdate(BaseModel):
    nome: str | None = None
    relacao: str | None = None
    notas: str | None = None
    metadados: dict | None = None
    numero_whatsapp: str | None = None
    flg_monitorar_whatsapp: bool | None = None


class PessoaResponse(BaseModel):
    id: uuid.UUID
    cod_pessoa: int
    nome: str
    relacao: str | None
    notas: str | None
    metadados: dict | None
    numero_whatsapp: str | None
    flg_monitorar_whatsapp: bool
    flg_ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class EventoCreate(BaseModel):
    dat_ocorreu: datetime
    resumo: str
    categoria: str
    lojas: list[str] | None = None
    pessoas_envolvidas: list[uuid.UUID] | None = None
    metadados: dict | None = None


class EventoUpdate(BaseModel):
    dat_ocorreu: datetime | None = None
    resumo: str | None = None
    categoria: str | None = None
    lojas: list[str] | None = None
    pessoas_envolvidas: list[uuid.UUID] | None = None
    metadados: dict | None = None


class EventoResponse(BaseModel):
    id: uuid.UUID
    dat_ocorreu: datetime
    resumo: str
    categoria: str
    lojas: list[str] | None
    pessoas_envolvidas: list[uuid.UUID] | None
    metadados: dict | None
    flg_ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}
