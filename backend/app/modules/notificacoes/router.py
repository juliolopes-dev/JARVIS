import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.notificacoes import service
from app.modules.notificacoes.schemas import SubscricaoCreate, SubscricaoRemover, HistoricoNotificacaoResponse

router = APIRouter()


@router.get("/vapid-public-key", summary="Chave publica VAPID para o frontend")
async def vapid_public_key():
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe", summary="Registrar subscricao push")
async def subscribe(
    dados: SubscricaoCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.salvar_subscricao(
        usuario.id, dados.endpoint, dados.chave_p256dh, dados.chave_auth, dados.dispositivo, db,
    )
    await db.commit()
    return {"success": True}


@router.post("/unsubscribe", summary="Remover subscricao push")
async def unsubscribe(
    dados: SubscricaoRemover,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.remover_subscricao(dados.endpoint, usuario.id, db)
    await db.commit()
    return {"success": True}


# ─── Historico ────────────────────────────────────────────────────────────────

@router.get("/historico", response_model=list[HistoricoNotificacaoResponse])
async def listar_historico(
    apenas_nao_lidas: bool = False,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_historico(usuario.id, db, apenas_nao_lidas)


@router.get("/historico/nao-lidas", summary="Contagem de nao lidas")
async def contar_nao_lidas(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await service.contar_nao_lidas(usuario.id, db)
    return {"total": total}


@router.patch("/historico/{id_notif}/lida", summary="Marcar notificacao como lida")
async def marcar_lida(
    id_notif: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.marcar_lida(id_notif, usuario.id, db)
    return {"success": True}


@router.post("/historico/marcar-todas-lidas", summary="Marcar todas como lidas")
async def marcar_todas_lidas(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = await service.marcar_todas_lidas(usuario.id, db)
    return {"success": True, "marcadas": total}


@router.post("/testar-push", summary="Envia push de teste para todos os dispositivos ativos")
async def testar_push(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.core.webpush import enviar_push
    from app.modules.notificacoes.models import SubscricaoPush

    result = await db.execute(
        select(SubscricaoPush).where(
            SubscricaoPush.id_usuario == usuario.id,
            SubscricaoPush.flg_ativo == True,  # noqa: E712
        )
    )
    subscricoes = result.scalars().all()

    if not subscricoes:
        return {"success": False, "erro": "Nenhuma subscricao ativa encontrada", "total": 0}

    payload = {
        "title": "🔔 Teste Jarvis",
        "body": "Notificação push funcionando!",
        "url": "/notificacoes",
    }

    resultados = []
    for sub in subscricoes:
        ok = enviar_push(sub.endpoint, sub.chave_p256dh, sub.chave_auth, payload)
        if not ok:
            sub.flg_ativo = False
            db.add(sub)
        resultados.append({"dispositivo": sub.dispositivo, "ok": ok})

    await db.commit()
    return {"success": True, "total_subscricoes": len(subscricoes), "resultados": resultados}
