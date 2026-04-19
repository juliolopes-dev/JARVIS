"""
Backfill de eventos a partir das mensagens historicas do chat.

Percorre todas as mensagens do usuario com papel='user', roda detectar_evento
em cada uma e cria Evento quando aplicavel. Usa criado_em da mensagem como
dat_ocorreu (heuristica razoavel: quando o Julio relatou, o evento era recente).

Uso:
    cd backend && uv run python scripts/backfill_eventos.py [--dry-run] [--since-days N] [--limit N]

Flags:
    --dry-run      Nao cria nada, apenas lista o que seria criado
    --since-days N Processa apenas mensagens dos ultimos N dias (padrao: todas)
    --limit N      Limita o numero de mensagens processadas (util para teste)

Idempotente: antes de criar, verifica se ja existe evento com mesmo resumo
para o mesmo usuario (evita duplicar em re-execucoes).
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402

# Importar todos os modelos para o SQLAlchemy resolver relacionamentos
import app.modules.auth.models  # noqa: E402, F401
import app.modules.chat.models  # noqa: E402, F401
import app.modules.checklist.models  # noqa: E402, F401
import app.modules.config.models  # noqa: E402, F401
import app.modules.lembretes.models  # noqa: E402, F401
import app.modules.livros.models  # noqa: E402, F401
import app.modules.notificacoes.models  # noqa: E402, F401
import app.modules.tarefas.models  # noqa: E402, F401

from app.modules.auth.models import Usuario  # noqa: E402
from app.modules.chat.models import Mensagem  # noqa: E402
from app.modules.memoria.models import Evento  # noqa: E402
from app.modules.memoria.schemas import EventoCreate  # noqa: E402
from app.modules.memoria.service import criar_evento  # noqa: E402
from app.modules.ia.service import detectar_evento  # noqa: E402


async def _ja_existe(resumo: str, id_usuario, db) -> bool:
    """Evita duplicacao em re-execucao."""
    result = await db.execute(
        select(Evento).where(
            Evento.id_usuario == id_usuario,
            Evento.resumo == resumo,
            Evento.flg_ativo == True,  # noqa: E712
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def processar(dry_run: bool, since_days: int | None, limit: int | None) -> None:
    async with AsyncSessionLocal() as db:
        # Usuario unico
        result = await db.execute(select(Usuario).limit(1))
        usuario = result.scalar_one_or_none()
        if not usuario:
            print("ERRO: nenhum usuario cadastrado.")
            return

        print(f"Usuario: {usuario.email}")

        query = select(Mensagem).where(Mensagem.papel == "user").order_by(Mensagem.criado_em.asc())
        if since_days:
            corte = datetime.now(timezone.utc) - timedelta(days=since_days)
            query = query.where(Mensagem.criado_em >= corte)
        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        mensagens = list(result.scalars())
        print(f"Mensagens a processar: {len(mensagens)}")
        print()

        criados = 0
        pulados_duplicados = 0
        nao_eh_evento = 0
        erros = 0

        for i, msg in enumerate(mensagens, 1):
            conteudo = (msg.conteudo or "").strip()
            if len(conteudo) < 10:
                nao_eh_evento += 1
                continue

            print(f"[{i}/{len(mensagens)}] {conteudo[:80]}...")

            try:
                evento_info = await detectar_evento(conteudo)
            except Exception as e:
                print(f"  [ERRO deteccao] {e}")
                erros += 1
                continue

            if not evento_info:
                nao_eh_evento += 1
                continue

            resumo = evento_info["resumo"]

            if await _ja_existe(resumo, usuario.id, db):
                print(f"  [DUPLICADO] {resumo}")
                pulados_duplicados += 1
                continue

            if dry_run:
                lojas = evento_info.get("lojas") or []
                print(f"  [DRY-RUN] {evento_info.get('categoria')}: {resumo} | lojas={lojas}")
                criados += 1
                continue

            try:
                lojas = evento_info.get("lojas") or None
                if isinstance(lojas, list) and len(lojas) == 0:
                    lojas = None

                dados = EventoCreate(
                    dat_ocorreu=msg.criado_em,  # usa data da mensagem como proxy
                    resumo=resumo,
                    categoria=evento_info.get("categoria", "outro"),
                    lojas=lojas,
                    metadados={"origem": "backfill", "id_mensagem_origem": str(msg.id)},
                )
                evt = await criar_evento(dados, usuario.id, db)
                await db.commit()
                print(f"  [CRIADO] {evt.categoria}: {evt.resumo}")
                criados += 1
            except Exception as e:
                await db.rollback()
                print(f"  [ERRO criacao] {e}")
                erros += 1

        print()
        print("=" * 60)
        print(f"Criados:          {criados}")
        print(f"Duplicados:       {pulados_duplicados}")
        print(f"Nao sao eventos:  {nao_eh_evento}")
        print(f"Erros:            {erros}")
        if dry_run:
            print()
            print("[DRY-RUN] Nada foi gravado no banco. Rode sem --dry-run para aplicar.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill de eventos a partir do historico de chat")
    parser.add_argument("--dry-run", action="store_true", help="Nao cria nada, so lista")
    parser.add_argument("--since-days", type=int, default=None, help="Processa apenas ultimos N dias")
    parser.add_argument("--limit", type=int, default=None, help="Limita numero de mensagens")
    args = parser.parse_args()

    asyncio.run(processar(args.dry_run, args.since_days, args.limit))


if __name__ == "__main__":
    main()
