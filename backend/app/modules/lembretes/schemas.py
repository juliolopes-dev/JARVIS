import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class LembreteCreate(BaseModel):
    titulo: str
    descricao: str | None = None
    dat_lembrete: datetime

    @field_validator("dat_lembrete")
    @classmethod
    def validar_data_futura(cls, v: datetime) -> datetime:
        from datetime import timezone
        agora = datetime.now(timezone.utc)
        if v.tzinfo is None:
            # Assumir America/Sao_Paulo se sem timezone
            from zoneinfo import ZoneInfo
            v = v.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        if v <= agora:
            raise ValueError("A data do lembrete deve ser no futuro")
        return v


class LembreteUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    dat_lembrete: datetime | None = None


class LembreteResponse(BaseModel):
    id: uuid.UUID
    titulo: str
    descricao: str | None
    dat_lembrete: datetime
    sts_lembrete: str
    criado_em: datetime

    model_config = {"from_attributes": True}


# Schema usado pelo chat para criar lembrete via linguagem natural
class LembreteParsed(BaseModel):
    titulo: str
    descricao: str | None = None
    dat_lembrete: datetime
