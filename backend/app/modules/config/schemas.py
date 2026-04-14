import uuid
from datetime import datetime

from pydantic import BaseModel


class ConfiguracaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    modelo_preferido: str
    tema: str
    flg_briefing_diario: bool
    horario_briefing: str  # "HH:MM"
    flg_notificacoes: bool
    criado_em: datetime
    atualizado_em: datetime


class ConfiguracaoUpdate(BaseModel):
    modelo_preferido: str | None = None
    tema: str | None = None
    flg_briefing_diario: bool | None = None
    horario_briefing: str | None = None  # "HH:MM"
    flg_notificacoes: bool | None = None
