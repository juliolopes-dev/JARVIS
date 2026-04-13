import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TarefaAgendada(Base):
    __tablename__ = "tarefas_agendadas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    descricao: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(50))  # 'briefing', 'monitoramento', 'lembrete'
    cron_expressao: Mapped[str | None] = mapped_column(String(100))
    parametros: Mapped[dict | None] = mapped_column(JSONB)
    sts_tarefa: Mapped[str] = mapped_column(String(20), default="ativa", index=True)
    dat_ultima_execucao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dat_proxima_execucao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
