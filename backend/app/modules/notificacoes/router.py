from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.notificacoes import service
from app.modules.notificacoes.schemas import SubscricaoCreate, SubscricaoRemover

router = APIRouter()


@router.get("/vapid-public-key", summary="Chave publica VAPID para o frontend")
async def vapid_public_key():
    """Retorna a chave publica VAPID para o frontend se inscrever no push."""
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe", summary="Registrar subscricao push")
async def subscribe(
    dados: SubscricaoCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.salvar_subscricao(
        usuario.id,
        dados.endpoint,
        dados.chave_p256dh,
        dados.chave_auth,
        dados.dispositivo,
        db,
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
