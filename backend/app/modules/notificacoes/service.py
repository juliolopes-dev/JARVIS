"""
Service de Notificacoes — gerencia subscricoes Web Push.
"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notificacoes.models import SubscricaoPush


async def salvar_subscricao(
    id_usuario: uuid.UUID,
    endpoint: str,
    chave_p256dh: str,
    chave_auth: str,
    dispositivo: str | None,
    db: AsyncSession,
) -> SubscricaoPush:
    """Salva ou atualiza subscricao push (unico endpoint por dispositivo)."""
    # Verificar se ja existe
    result = await db.execute(
        select(SubscricaoPush).where(
            SubscricaoPush.endpoint == endpoint,
        )
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.chave_p256dh = chave_p256dh
        sub.chave_auth = chave_auth
        sub.flg_ativo = True
        if dispositivo:
            sub.dispositivo = dispositivo
    else:
        sub = SubscricaoPush(
            id_usuario=id_usuario,
            endpoint=endpoint,
            chave_p256dh=chave_p256dh,
            chave_auth=chave_auth,
            dispositivo=dispositivo,
        )
        db.add(sub)

    logger.info("Subscricao push salva | usuario={} | dispositivo={}", id_usuario, dispositivo)
    return sub


async def remover_subscricao(endpoint: str, id_usuario: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(
        select(SubscricaoPush).where(
            SubscricaoPush.endpoint == endpoint,
            SubscricaoPush.id_usuario == id_usuario,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return False
    sub.flg_ativo = False
    db.add(sub)
    return True
