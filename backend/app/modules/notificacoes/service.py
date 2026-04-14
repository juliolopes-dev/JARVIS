"""
Service de Notificacoes — gerencia subscricoes Web Push e historico de notificacoes.
"""

import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notificacoes.models import SubscricaoPush, HistoricoNotificacao


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


# ─── Historico de Notificacoes ────────────────────────────────────────────────

async def salvar_historico(
    id_usuario: uuid.UUID,
    tipo: str,
    titulo: str,
    corpo: str | None,
    db: AsyncSession,
) -> HistoricoNotificacao:
    """Salva notificacao no historico antes de disparar o push."""
    notif = HistoricoNotificacao(
        id_usuario=id_usuario,
        tipo=tipo,
        titulo=titulo,
        corpo=corpo,
    )
    db.add(notif)
    await db.flush()
    return notif


async def listar_historico(
    id_usuario: uuid.UUID,
    db: AsyncSession,
    apenas_nao_lidas: bool = False,
    limite: int = 50,
) -> list[HistoricoNotificacao]:
    query = select(HistoricoNotificacao).where(
        HistoricoNotificacao.id_usuario == id_usuario,
    )
    if apenas_nao_lidas:
        query = query.where(HistoricoNotificacao.flg_lida == False)  # noqa: E712
    query = query.order_by(HistoricoNotificacao.criado_em.desc()).limit(limite)
    result = await db.execute(query)
    return list(result.scalars())


async def marcar_lida(
    id_notif: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(HistoricoNotificacao).where(
            HistoricoNotificacao.id == id_notif,
            HistoricoNotificacao.id_usuario == id_usuario,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.flg_lida = True
    notif.dat_lida = datetime.now(timezone.utc)
    db.add(notif)
    return True


async def marcar_todas_lidas(id_usuario: uuid.UUID, db: AsyncSession) -> int:
    """Marca todas as nao lidas como lidas. Retorna quantas foram marcadas."""
    result = await db.execute(
        select(HistoricoNotificacao).where(
            HistoricoNotificacao.id_usuario == id_usuario,
            HistoricoNotificacao.flg_lida == False,  # noqa: E712
        )
    )
    notifs = result.scalars().all()
    agora = datetime.now(timezone.utc)
    for n in notifs:
        n.flg_lida = True
        n.dat_lida = agora
        db.add(n)
    return len(notifs)


async def contar_nao_lidas(id_usuario: uuid.UUID, db: AsyncSession) -> int:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count()).where(
            HistoricoNotificacao.id_usuario == id_usuario,
            HistoricoNotificacao.flg_lida == False,  # noqa: E712
        )
    )
    return result.scalar() or 0
