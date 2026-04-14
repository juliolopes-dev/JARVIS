import uuid
from datetime import datetime

from pydantic import BaseModel


class SubscricaoCreate(BaseModel):
    endpoint: str
    chave_p256dh: str
    chave_auth: str
    dispositivo: str | None = None


class SubscricaoRemover(BaseModel):
    endpoint: str


class HistoricoNotificacaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tipo: str
    titulo: str
    corpo: str | None
    flg_lida: bool
    dat_lida: datetime | None
    criado_em: datetime
