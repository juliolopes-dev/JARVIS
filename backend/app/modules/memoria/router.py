import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.memoria import service
from app.modules.memoria.schemas import (
    EventoCreate,
    EventoResponse,
    EventoUpdate,
    MemoriaResponse,
    PessoaCreate,
    PessoaResponse,
    PessoaUpdate,
)

router = APIRouter()


@router.get("/buscar", response_model=list[MemoriaResponse])
async def buscar_memorias(
    q: str = Query(..., min_length=2),
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Busca semantica nas memorias do usuario."""
    memorias = await service.listar_memorias(usuario.id, db)
    # Retorna todas por agora; a busca semantica e chamada pelo modulo chat
    return memorias


@router.get("", response_model=list[MemoriaResponse])
async def listar_memorias(
    categoria: str | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista memorias do usuario com filtro por categoria."""
    return await service.listar_memorias(usuario.id, db, categoria, pagina, por_pagina)


@router.delete("/{id_memoria}")
async def desativar_memoria(
    id_memoria: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desativa (soft delete) uma memoria."""
    ok = await service.desativar_memoria(id_memoria, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Memoria nao encontrada")
    return {"success": True}


@router.get("/pessoas", response_model=list[PessoaResponse])
async def listar_pessoas(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_pessoas(usuario.id, db)


@router.post("/pessoas", response_model=PessoaResponse, status_code=201)
async def criar_pessoa(
    dados: PessoaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.criar_pessoa(dados, usuario.id, db)


@router.get("/pessoas/{id_pessoa}", response_model=PessoaResponse)
async def buscar_pessoa(
    id_pessoa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pessoa = await service.buscar_pessoa(id_pessoa, usuario.id, db)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")
    return pessoa


@router.put("/pessoas/{id_pessoa}", response_model=PessoaResponse)
async def atualizar_pessoa(
    id_pessoa: uuid.UUID,
    dados: PessoaUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pessoa = await service.atualizar_pessoa(id_pessoa, dados, usuario.id, db)
    if not pessoa:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")
    return pessoa


@router.delete("/pessoas/{id_pessoa}")
async def desativar_pessoa(
    id_pessoa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.desativar_pessoa(id_pessoa, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")
    return {"success": True}


# ===== EVENTOS =====

@router.get("/eventos", response_model=list[EventoResponse])
async def listar_eventos(
    categoria: str | None = Query(None),
    loja: str | None = Query(None),
    id_pessoa: uuid.UUID | None = Query(None),
    dat_inicio: datetime | None = Query(None),
    dat_fim: datetime | None = Query(None),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=100),
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_eventos(
        usuario.id, db, categoria, loja, id_pessoa, dat_inicio, dat_fim, pagina, por_pagina
    )


@router.post("/eventos", response_model=EventoResponse, status_code=201)
async def criar_evento(
    dados: EventoCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.criar_evento(dados, usuario.id, db)


@router.get("/eventos/{id_evento}", response_model=EventoResponse)
async def buscar_evento(
    id_evento: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evento = await service.buscar_evento(id_evento, usuario.id, db)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento nao encontrado")
    return evento


@router.put("/eventos/{id_evento}", response_model=EventoResponse)
async def atualizar_evento(
    id_evento: uuid.UUID,
    dados: EventoUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    evento = await service.atualizar_evento(id_evento, dados, usuario.id, db)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento nao encontrado")
    return evento


@router.delete("/eventos/{id_evento}")
async def desativar_evento(
    id_evento: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.desativar_evento(id_evento, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Evento nao encontrado")
    return {"success": True}
