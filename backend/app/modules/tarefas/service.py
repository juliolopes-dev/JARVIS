"""
Service de Tarefas Agendadas — tarefas recorrentes via cron + APScheduler + Web Push.
Diferente do modulo 'lembretes' (pontual) e 'checklist' (lista de tarefas sem agenda).
"""

import uuid
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scheduler import scheduler
from app.modules.tarefas.models import TarefaAgendada
from app.modules.tarefas.schemas import TarefaAgendadaCreate, TarefaAgendadaUpdate

TIMEZONE = "America/Sao_Paulo"


# ─── Job executado pelo APScheduler ───────────────────────────────────────────

async def _disparar_tarefa(id_tarefa: str, id_usuario: str) -> None:
    """Executado pelo APScheduler no cron da tarefa. Envia push."""
    from app.core.database import AsyncSessionLocal
    from app.core.webpush import enviar_push
    from app.modules.notificacoes.models import SubscricaoPush
    from app.modules.notificacoes.service import salvar_historico

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(TarefaAgendada).where(
                    TarefaAgendada.id == uuid.UUID(id_tarefa),
                    TarefaAgendada.sts_tarefa == "ativa",
                )
            )
            tarefa = result.scalar_one_or_none()
            if not tarefa:
                return

            # Payload do push vem de parametros.texto_push ou da descricao
            texto = (tarefa.parametros or {}).get("texto_push") or tarefa.descricao
            titulo = (tarefa.parametros or {}).get("titulo_push") or "🔔 Tarefa recorrente"

            result_subs = await db.execute(
                select(SubscricaoPush).where(
                    SubscricaoPush.id_usuario == uuid.UUID(id_usuario),
                    SubscricaoPush.flg_ativo == True,  # noqa: E712
                )
            )
            subscricoes = result_subs.scalars().all()

            payload = {
                "title": titulo,
                "body": texto,
                "id_tarefa": id_tarefa,
                "url": "/tarefas-agendadas",
            }

            await salvar_historico(
                uuid.UUID(id_usuario), "tarefa_recorrente", titulo, texto, db
            )

            for sub in subscricoes:
                sucesso = enviar_push(sub.endpoint, sub.chave_p256dh, sub.chave_auth, payload)
                if not sucesso:
                    sub.flg_ativo = False
                    db.add(sub)

            # Atualizar dat_ultima_execucao e dat_proxima_execucao
            tarefa.dat_ultima_execucao = datetime.now()
            job = scheduler.get_job(tarefa.parametros.get("job_id") if tarefa.parametros else f"tarefa_{id_tarefa}")
            if job and job.next_run_time:
                tarefa.dat_proxima_execucao = job.next_run_time
            db.add(tarefa)
            await db.commit()

            logger.info("Tarefa disparada | id={} | descricao={}", id_tarefa, tarefa.descricao)

        except Exception as e:
            await db.rollback()
            logger.error("Erro ao disparar tarefa {} | erro={}", id_tarefa, str(e))


# ─── Scheduler helpers ────────────────────────────────────────────────────────

def _agendar_job(tarefa: TarefaAgendada) -> datetime | None:
    """Registra o job no APScheduler. Retorna dat_proxima_execucao."""
    job_id = f"tarefa_{tarefa.id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    trigger = CronTrigger.from_crontab(tarefa.cron_expressao, timezone=TIMEZONE)
    job = scheduler.add_job(
        _disparar_tarefa,
        trigger=trigger,
        args=[str(tarefa.id), str(tarefa.id_usuario)],
        id=job_id,
        replace_existing=True,
    )
    return job.next_run_time


def _remover_job(tarefa_id: uuid.UUID) -> None:
    job_id = f"tarefa_{tarefa_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def criar_tarefa(
    dados: TarefaAgendadaCreate,
    id_usuario: uuid.UUID,
    db: AsyncSession,
    tipo: str = "lembrete",
) -> TarefaAgendada:
    tarefa = TarefaAgendada(
        id_usuario=id_usuario,
        descricao=dados.descricao,
        tipo=tipo,
        cron_expressao=dados.cron_expressao,
        parametros=dados.parametros or {},
        sts_tarefa="ativa",
    )
    db.add(tarefa)
    await db.flush()

    proxima = _agendar_job(tarefa)
    tarefa.dat_proxima_execucao = proxima
    db.add(tarefa)

    logger.info(
        "Tarefa agendada criada | id={} | cron={} | proxima={}",
        tarefa.id, dados.cron_expressao, proxima
    )
    return tarefa


async def listar_tarefas(
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> list[TarefaAgendada]:
    result = await db.execute(
        select(TarefaAgendada)
        .where(TarefaAgendada.id_usuario == id_usuario)
        .order_by(TarefaAgendada.criado_em.desc())
    )
    return list(result.scalars())


async def buscar_tarefa(
    id_tarefa: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> TarefaAgendada | None:
    result = await db.execute(
        select(TarefaAgendada).where(
            TarefaAgendada.id == id_tarefa,
            TarefaAgendada.id_usuario == id_usuario,
        )
    )
    return result.scalar_one_or_none()


async def atualizar_tarefa(
    id_tarefa: uuid.UUID,
    dados: TarefaAgendadaUpdate,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> TarefaAgendada | None:
    tarefa = await buscar_tarefa(id_tarefa, id_usuario, db)
    if not tarefa:
        return None

    cron_mudou = False
    if dados.descricao is not None:
        tarefa.descricao = dados.descricao
    if dados.cron_expressao is not None and dados.cron_expressao != tarefa.cron_expressao:
        tarefa.cron_expressao = dados.cron_expressao
        cron_mudou = True
    if dados.parametros is not None:
        tarefa.parametros = dados.parametros
    if dados.sts_tarefa is not None:
        tarefa.sts_tarefa = dados.sts_tarefa
        if dados.sts_tarefa == "pausada":
            _remover_job(tarefa.id)
            tarefa.dat_proxima_execucao = None
        elif dados.sts_tarefa == "ativa":
            cron_mudou = True  # re-agendar

    if cron_mudou and tarefa.sts_tarefa == "ativa":
        proxima = _agendar_job(tarefa)
        tarefa.dat_proxima_execucao = proxima

    db.add(tarefa)
    return tarefa


async def deletar_tarefa(
    id_tarefa: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> bool:
    tarefa = await buscar_tarefa(id_tarefa, id_usuario, db)
    if not tarefa:
        return False
    _remover_job(tarefa.id)
    await db.delete(tarefa)
    return True


async def reagendar_todas(db: AsyncSession) -> int:
    """
    Chamado no startup — reagenda todas as tarefas ativas no scheduler.
    Retorna quantas foram reagendadas.
    """
    result = await db.execute(
        select(TarefaAgendada).where(TarefaAgendada.sts_tarefa == "ativa")
    )
    tarefas = result.scalars().all()
    total = 0
    for tarefa in tarefas:
        try:
            proxima = _agendar_job(tarefa)
            tarefa.dat_proxima_execucao = proxima
            db.add(tarefa)
            total += 1
        except Exception as e:
            logger.warning("Falha ao reagendar tarefa {}: {}", tarefa.id, str(e))
    return total
