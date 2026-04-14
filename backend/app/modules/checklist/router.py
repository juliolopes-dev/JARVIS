import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.checklist import service
from app.modules.checklist.schemas import (
    ListaCreate, ListaUpdate, ListaResponse,
    TarefaCreate, TarefaUpdate, TarefaResponse,
)

router = APIRouter()


# ─── Listas ───────────────────────────────────────────────────────────────────

@router.get("/listas", response_model=list[ListaResponse])
async def listar_listas(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_listas(usuario.id, db)


@router.post("/listas", response_model=ListaResponse, status_code=201)
async def criar_lista(
    dados: ListaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.criar_lista(usuario.id, dados, db)


@router.put("/listas/{id_lista}", response_model=ListaResponse)
async def atualizar_lista(
    id_lista: uuid.UUID,
    dados: ListaUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lista = await service.atualizar_lista(id_lista, usuario.id, dados, db)
    if not lista:
        raise HTTPException(status_code=404, detail="Lista nao encontrada")
    return lista


@router.delete("/listas/{id_lista}")
async def deletar_lista(
    id_lista: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.deletar_lista(id_lista, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Lista nao encontrada")
    return {"success": True}


# ─── Tarefas ──────────────────────────────────────────────────────────────────

@router.get("/tarefas", response_model=list[TarefaResponse])
async def listar_tarefas(
    id_lista: uuid.UUID | None = None,
    concluidas: bool | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_tarefas(usuario.id, db, id_lista, concluidas)


@router.post("/tarefas", response_model=TarefaResponse, status_code=201)
async def criar_tarefa(
    dados: TarefaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.criar_tarefa(dados, usuario.id, db)


@router.patch("/tarefas/{id_tarefa}/concluir", response_model=TarefaResponse)
async def concluir_tarefa(
    id_tarefa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tarefa = await service.concluir_tarefa(id_tarefa, usuario.id, db)
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    return tarefa


@router.put("/tarefas/{id_tarefa}", response_model=TarefaResponse)
async def atualizar_tarefa(
    id_tarefa: uuid.UUID,
    dados: TarefaUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tarefa = await service.atualizar_tarefa(id_tarefa, usuario.id, dados, db)
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    return tarefa


@router.delete("/tarefas/{id_tarefa}")
async def deletar_tarefa(
    id_tarefa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.deletar_tarefa(id_tarefa, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    return {"success": True}
