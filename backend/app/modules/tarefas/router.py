import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.tarefas import service
from app.modules.tarefas.schemas import (
    TarefaAgendadaCreate,
    TarefaAgendadaResponse,
    TarefaAgendadaUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[TarefaAgendadaResponse])
async def listar(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.listar_tarefas(usuario.id, db)


@router.post("/", response_model=TarefaAgendadaResponse, status_code=201)
async def criar(
    dados: TarefaAgendadaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tarefa = await service.criar_tarefa(dados, usuario.id, db)
    await db.commit()
    await db.refresh(tarefa)
    return tarefa


@router.put("/{id_tarefa}", response_model=TarefaAgendadaResponse)
async def atualizar(
    id_tarefa: uuid.UUID,
    dados: TarefaAgendadaUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tarefa = await service.atualizar_tarefa(id_tarefa, dados, usuario.id, db)
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    await db.commit()
    await db.refresh(tarefa)
    return tarefa


@router.delete("/{id_tarefa}")
async def deletar(
    id_tarefa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.deletar_tarefa(id_tarefa, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    await db.commit()
    return {"success": True}


@router.post("/{id_tarefa}/executar", status_code=202)
async def executar_agora(
    id_tarefa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dispara a tarefa imediatamente (teste manual)."""
    tarefa = await service.buscar_tarefa(id_tarefa, usuario.id, db)
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    await service._disparar_tarefa(str(tarefa.id), str(usuario.id))
    return {"success": True}
