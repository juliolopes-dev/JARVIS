"""
Service de Lembretes — CRUD + agendamento APScheduler + disparo Web Push.
"""

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scheduler import scheduler
from app.modules.lembretes.models import Lembrete
from app.modules.lembretes.schemas import LembreteCreate, LembreteUpdate


# ─── Job executado pelo APScheduler no horario do lembrete ───────────────────

async def _disparar_lembrete(id_lembrete: str, id_usuario: str) -> None:
    """Executado pelo APScheduler. Envia push e marca lembrete como disparado."""
    from app.core.database import AsyncSessionLocal
    from app.core.webpush import enviar_push
    from app.modules.notificacoes.models import SubscricaoPush

    async with AsyncSessionLocal() as db:
        try:
            # Buscar lembrete
            result = await db.execute(
                select(Lembrete).where(
                    Lembrete.id == uuid.UUID(id_lembrete),
                    Lembrete.flg_ativo == True,  # noqa: E712
                )
            )
            lembrete = result.scalar_one_or_none()
            if not lembrete or lembrete.sts_lembrete != "pendente":
                return

            # Buscar subscricoes ativas do usuario
            result_subs = await db.execute(
                select(SubscricaoPush).where(
                    SubscricaoPush.id_usuario == uuid.UUID(id_usuario),
                    SubscricaoPush.flg_ativo == True,  # noqa: E712
                )
            )
            subscricoes = result_subs.scalars().all()

            # Payload da notificacao
            payload = {
                "title": f"⏰ {lembrete.titulo}",
                "body": lembrete.descricao or lembrete.titulo,
                "id_lembrete": id_lembrete,
                "url": "/lembretes",
            }

            # Enviar push para cada dispositivo
            for sub in subscricoes:
                sucesso = enviar_push(sub.endpoint, sub.chave_p256dh, sub.chave_auth, payload)
                if not sucesso:
                    # Subscricao expirou — desativar
                    sub.flg_ativo = False
                    db.add(sub)

            # Marcar lembrete como disparado
            lembrete.sts_lembrete = "disparado"
            db.add(lembrete)
            await db.commit()

            logger.info("Lembrete disparado | id={} | titulo={}", id_lembrete, lembrete.titulo)

        except Exception as e:
            await db.rollback()
            logger.error("Erro ao disparar lembrete {} | erro={}", id_lembrete, str(e))


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def criar_lembrete(
    dados: LembreteCreate,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> Lembrete:
    lembrete = Lembrete(
        id_usuario=id_usuario,
        titulo=dados.titulo,
        descricao=dados.descricao,
        dat_lembrete=dados.dat_lembrete,
    )
    db.add(lembrete)
    await db.flush()  # Gera o UUID

    # Agendar job no APScheduler
    job_id = f"lembrete_{lembrete.id}"
    scheduler.add_job(
        _disparar_lembrete,
        trigger="date",
        run_date=dados.dat_lembrete,
        args=[str(lembrete.id), str(id_usuario)],
        id=job_id,
        replace_existing=True,
    )
    lembrete.id_job = job_id
    db.add(lembrete)

    logger.info(
        "Lembrete criado | id={} | titulo={} | dat={}",
        lembrete.id, lembrete.titulo, dados.dat_lembrete
    )
    return lembrete


async def listar_lembretes(
    id_usuario: uuid.UUID,
    db: AsyncSession,
    apenas_pendentes: bool = False,
    pagina: int = 1,
    por_pagina: int = 20,
) -> list[Lembrete]:
    query = select(Lembrete).where(
        Lembrete.id_usuario == id_usuario,
        Lembrete.flg_ativo == True,  # noqa: E712
    )
    if apenas_pendentes:
        query = query.where(Lembrete.sts_lembrete == "pendente")

    query = query.order_by(Lembrete.dat_lembrete.asc())
    query = query.offset((pagina - 1) * por_pagina).limit(por_pagina)

    result = await db.execute(query)
    return list(result.scalars())


async def buscar_lembrete(
    id_lembrete: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> Lembrete | None:
    result = await db.execute(
        select(Lembrete).where(
            Lembrete.id == id_lembrete,
            Lembrete.id_usuario == id_usuario,
            Lembrete.flg_ativo == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def atualizar_lembrete(
    id_lembrete: uuid.UUID,
    dados: LembreteUpdate,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> Lembrete | None:
    lembrete = await buscar_lembrete(id_lembrete, id_usuario, db)
    if not lembrete or lembrete.sts_lembrete != "pendente":
        return None

    if dados.titulo is not None:
        lembrete.titulo = dados.titulo
    if dados.descricao is not None:
        lembrete.descricao = dados.descricao
    if dados.dat_lembrete is not None:
        lembrete.dat_lembrete = dados.dat_lembrete
        # Re-agendar job
        if lembrete.id_job:
            try:
                scheduler.remove_job(lembrete.id_job)
            except Exception:
                pass
        job_id = f"lembrete_{lembrete.id}"
        scheduler.add_job(
            _disparar_lembrete,
            trigger="date",
            run_date=dados.dat_lembrete,
            args=[str(lembrete.id), str(id_usuario)],
            id=job_id,
            replace_existing=True,
        )
        lembrete.id_job = job_id

    db.add(lembrete)
    return lembrete


async def cancelar_lembrete(
    id_lembrete: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> bool:
    lembrete = await buscar_lembrete(id_lembrete, id_usuario, db)
    if not lembrete:
        return False

    # Remover job do scheduler
    if lembrete.id_job:
        try:
            scheduler.remove_job(lembrete.id_job)
        except Exception:
            pass

    lembrete.sts_lembrete = "cancelado"
    lembrete.flg_ativo = False
    db.add(lembrete)
    return True
