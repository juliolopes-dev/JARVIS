import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.lembretes import service
from app.modules.lembretes.schemas import LembreteCreate, LembreteResponse, LembreteUpdate

router = APIRouter()


@router.get("", response_model=list[LembreteResponse], summary="Listar lembretes")
async def listar(
    apenas_pendentes: bool = False,
    pagina: int = 1,
    por_pagina: int = 20,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_lembretes(usuario.id, db, apenas_pendentes, pagina, por_pagina)


@router.post("", response_model=LembreteResponse, status_code=status.HTTP_201_CREATED, summary="Criar lembrete")
async def criar(
    dados: LembreteCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lembrete = await service.criar_lembrete(dados, usuario.id, db)
    await db.commit()
    await db.refresh(lembrete)
    return lembrete


@router.patch("/{id_lembrete}", response_model=LembreteResponse, summary="Atualizar lembrete")
async def atualizar(
    id_lembrete: uuid.UUID,
    dados: LembreteUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lembrete = await service.atualizar_lembrete(id_lembrete, dados, usuario.id, db)
    if not lembrete:
        raise HTTPException(status_code=404, detail="Lembrete nao encontrado ou ja disparado")
    await db.commit()
    await db.refresh(lembrete)
    return lembrete


@router.delete("/{id_lembrete}", summary="Cancelar lembrete")
async def cancelar(
    id_lembrete: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.cancelar_lembrete(id_lembrete, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Lembrete nao encontrado")
    await db.commit()
    return {"success": True}
