"""
Service de Configuracoes — CRUD das preferencias do usuario.
"""

import uuid
from datetime import time

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.config.models import Configuracao
from app.modules.config.schemas import ConfiguracaoUpdate


async def obter_ou_criar_config(id_usuario: uuid.UUID, db: AsyncSession) -> Configuracao:
    """Retorna a configuracao do usuario, criando com defaults se nao existir."""
    result = await db.execute(
        select(Configuracao).where(Configuracao.id_usuario == id_usuario)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = Configuracao(id_usuario=id_usuario)
        db.add(config)
        await db.flush()
        logger.info("Configuracao criada com defaults | usuario={}", id_usuario)
    return config


def _horario_para_str(h: time) -> str:
    return h.strftime("%H:%M")


def _str_para_horario(s: str) -> time:
    hora, minuto = map(int, s.split(":"))
    return time(hora, minuto)


async def atualizar_config(
    id_usuario: uuid.UUID,
    dados: ConfiguracaoUpdate,
    db: AsyncSession,
) -> Configuracao:
    config = await obter_ou_criar_config(id_usuario, db)

    horario_mudou = False
    briefing_mudou = False

    if dados.modelo_preferido is not None:
        config.modelo_preferido = dados.modelo_preferido
    if dados.tema is not None:
        config.tema = dados.tema
    if dados.flg_notificacoes is not None:
        config.flg_notificacoes = dados.flg_notificacoes

    if dados.horario_briefing is not None:
        config.horario_briefing = _str_para_horario(dados.horario_briefing)
        horario_mudou = True

    if dados.flg_briefing_diario is not None:
        config.flg_briefing_diario = dados.flg_briefing_diario
        briefing_mudou = True

    db.add(config)

    # Re-agendar briefing se horario ou flag mudou
    if horario_mudou or briefing_mudou:
        from app.modules.briefing.service import agendar_briefing, cancelar_briefing
        if config.flg_briefing_diario:
            await agendar_briefing(id_usuario, _horario_para_str(config.horario_briefing))
        else:
            await cancelar_briefing(id_usuario)

    logger.info("Configuracao atualizada | usuario={}", id_usuario)
    return config
