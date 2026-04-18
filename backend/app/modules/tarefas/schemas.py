import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class TarefaAgendadaCreate(BaseModel):
    descricao: str
    cron_expressao: str
    parametros: dict | None = None

    @field_validator("cron_expressao")
    @classmethod
    def validar_cron(cls, v: str) -> str:
        partes = v.strip().split()
        if len(partes) != 5:
            raise ValueError("cron deve ter 5 campos: minuto hora dia mes dia_semana")
        return v.strip()


class TarefaAgendadaUpdate(BaseModel):
    descricao: str | None = None
    cron_expressao: str | None = None
    parametros: dict | None = None
    sts_tarefa: str | None = None

    @field_validator("cron_expressao")
    @classmethod
    def validar_cron(cls, v: str | None) -> str | None:
        if v is None:
            return v
        partes = v.strip().split()
        if len(partes) != 5:
            raise ValueError("cron deve ter 5 campos: minuto hora dia mes dia_semana")
        return v.strip()

    @field_validator("sts_tarefa")
    @classmethod
    def validar_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("ativa", "pausada"):
            raise ValueError("sts_tarefa deve ser 'ativa' ou 'pausada'")
        return v


class TarefaAgendadaResponse(BaseModel):
    id: uuid.UUID
    descricao: str
    tipo: str
    cron_expressao: str | None
    parametros: dict | None
    sts_tarefa: str
    dat_ultima_execucao: datetime | None
    dat_proxima_execucao: datetime | None
    criado_em: datetime

    model_config = {"from_attributes": True}


# Schema usado pelo chat para criar tarefa agendada via linguagem natural
class TarefaAgendadaParsed(BaseModel):
    descricao: str
    cron_expressao: str
    texto_push: str
