import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversaCreate(BaseModel):
    titulo: str | None = None


class ConversaResponse(BaseModel):
    id: uuid.UUID
    titulo: str | None
    flg_ativa: bool
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class MensagemCreate(BaseModel):
    conteudo: str


class MensagemResponse(BaseModel):
    id: uuid.UUID
    papel: str
    conteudo: str
    modelo_usado: str | None
    tokens_entrada: int | None
    tokens_saida: int | None
    criado_em: datetime

    model_config = {"from_attributes": True}
