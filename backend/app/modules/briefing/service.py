"""
Briefing diario — gera resumo do dia via IA e envia como Web Push.
Executado pelo APScheduler no horario configurado em configuracoes.horario_briefing.
"""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

BRT = ZoneInfo("America/Sao_Paulo")


async def gerar_texto_briefing(id_usuario: uuid.UUID, db) -> str:
    """Monta contexto do dia e pede ao GPT-4o um resumo executivo curto."""
    from sqlalchemy import select
    from app.modules.lembretes.models import Lembrete
    from app.modules.checklist.models import Tarefa
    from app.modules.ia.service import get_openai

    agora = datetime.now(BRT)
    hoje_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    hoje_fim = agora.replace(hour=23, minute=59, second=59, microsecond=0)

    # Lembretes pendentes para hoje
    result = await db.execute(
        select(Lembrete).where(
            Lembrete.id_usuario == id_usuario,
            Lembrete.flg_ativo == True,  # noqa: E712
            Lembrete.sts_lembrete == "pendente",
            Lembrete.dat_lembrete >= hoje_inicio,
            Lembrete.dat_lembrete <= hoje_fim,
        ).order_by(Lembrete.dat_lembrete)
    )
    lembretes_hoje = result.scalars().all()

    # Tarefas pendentes (sem data ou com vencimento hoje/atrasadas)
    result = await db.execute(
        select(Tarefa).where(
            Tarefa.id_usuario == id_usuario,
            Tarefa.flg_ativo == True,  # noqa: E712
            Tarefa.flg_concluida == False,  # noqa: E712
        ).order_by(Tarefa.prioridade.desc(), Tarefa.dat_vencimento)
        .limit(10)
    )
    tarefas_pendentes = result.scalars().all()

    # Montar contexto para a IA
    partes = []
    partes.append(f"Data: {agora.strftime('%A, %d de %B de %Y')} — {agora.strftime('%H:%M')} (Brasilia)")

    if lembretes_hoje:
        partes.append("\nLembretes para hoje:")
        for l in lembretes_hoje:
            hora = l.dat_lembrete.astimezone(BRT).strftime("%H:%M")
            partes.append(f"  - {hora}: {l.titulo}")
    else:
        partes.append("\nSem lembretes para hoje.")

    if tarefas_pendentes:
        partes.append("\nTarefas pendentes:")
        for t in tarefas_pendentes:
            prioridade = {"urgente": "🔴", "alta": "🟠", "media": "🔵", "baixa": "⚪"}.get(t.prioridade, "•")
            venc = ""
            if t.dat_vencimento:
                venc = f" (vence {t.dat_vencimento.astimezone(BRT).strftime('%d/%m')})"
            partes.append(f"  {prioridade} {t.titulo}{venc}")
    else:
        partes.append("\nSem tarefas pendentes.")

    contexto = "\n".join(partes)

    # Pedir resumo ao GPT-4o
    cliente = get_openai()
    response = await cliente.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Voce e o Jarvis, assistente pessoal do Julio. "
                    "Gere um briefing diario curto e direto em portugues do Brasil. "
                    "Tom: objetivo, como um chefe de gabinete passando o dia para o executivo. "
                    "Maximo 5 linhas. Sem markdown excessivo. Comece com uma saudacao adequada ao horario."
                ),
            },
            {"role": "user", "content": contexto},
        ],
        max_tokens=300,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


async def executar_briefing(id_usuario: str) -> None:
    """
    Job executado pelo APScheduler.
    Gera o briefing e envia como Web Push para todos os dispositivos ativos.
    """
    from app.core.database import AsyncSessionLocal
    from app.core.webpush import enviar_push
    from app.modules.notificacoes.models import SubscricaoPush
    from sqlalchemy import select

    uid = uuid.UUID(id_usuario)

    async with AsyncSessionLocal() as db:
        try:
            # Verificar se briefing ainda esta ativo para o usuario
            from app.modules.config.models import Configuracao
            result = await db.execute(
                select(Configuracao).where(Configuracao.id_usuario == uid)
            )
            config = result.scalar_one_or_none()
            if not config or not config.flg_briefing_diario:
                logger.info("Briefing desativado para usuario={}", id_usuario)
                return

            # Gerar texto
            texto = await gerar_texto_briefing(uid, db)
            logger.info("Briefing gerado | usuario={} | chars={}", id_usuario, len(texto))

            # Buscar subscricoes ativas
            result = await db.execute(
                select(SubscricaoPush).where(
                    SubscricaoPush.id_usuario == uid,
                    SubscricaoPush.flg_ativo == True,  # noqa: E712
                )
            )
            subscricoes = result.scalars().all()

            if not subscricoes:
                logger.info("Sem subscricoes push para briefing | usuario={}", id_usuario)
                return

            payload = {
                "title": "☀️ Briefing do dia",
                "body": texto[:150] + ("..." if len(texto) > 150 else ""),
                "texto_completo": texto,
                "url": "/chat",
            }

            for sub in subscricoes:
                sucesso = enviar_push(sub.endpoint, sub.chave_p256dh, sub.chave_auth, payload)
                if not sucesso:
                    sub.flg_ativo = False
                    db.add(sub)

            await db.commit()
            logger.info("Briefing enviado | usuario={} | dispositivos={}", id_usuario, len(subscricoes))

        except Exception as e:
            await db.rollback()
            logger.error("Erro ao executar briefing | usuario={} | erro={}", id_usuario, str(e))


async def agendar_briefing(id_usuario: uuid.UUID, horario_str: str) -> None:
    """
    Agenda (ou re-agenda) o job de briefing diario para o usuario.
    horario_str: "HH:MM" no fuso America/Sao_Paulo
    """
    from app.core.scheduler import scheduler

    job_id = f"briefing_{id_usuario}"
    hora, minuto = map(int, horario_str.split(":"))

    # Remover job anterior se existir
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    scheduler.add_job(
        executar_briefing,
        trigger="cron",
        hour=hora,
        minute=minuto,
        timezone="America/Sao_Paulo",
        args=[str(id_usuario)],
        id=job_id,
        replace_existing=True,
    )
    logger.info("Briefing agendado | usuario={} | horario={}:{:02d}", id_usuario, hora, minuto)


async def cancelar_briefing(id_usuario: uuid.UUID) -> None:
    """Remove o job de briefing do scheduler."""
    from app.core.scheduler import scheduler

    job_id = f"briefing_{id_usuario}"
    try:
        scheduler.remove_job(job_id)
        logger.info("Briefing cancelado | usuario={}", id_usuario)
    except Exception:
        pass
