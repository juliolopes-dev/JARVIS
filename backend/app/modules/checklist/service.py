"""
Service de Checklist — CRUD de Listas e Tarefas.
"""
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.checklist.models import Lista, Tarefa
from app.modules.checklist.schemas import ListaCreate, ListaUpdate, TarefaCreate, TarefaUpdate


# ─── Listas ───────────────────────────────────────────────────────────────────

async def listar_listas(id_usuario: uuid.UUID, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Lista).where(Lista.id_usuario == id_usuario, Lista.flg_ativo == True)
        .order_by(Lista.ordem, Lista.criado_em)
    )
    listas = result.scalars().all()

    out = []
    for lista in listas:
        # Contar tarefas
        total = await db.execute(
            select(func.count()).where(
                Tarefa.id_lista == lista.id, Tarefa.flg_ativo == True
            )
        )
        concluidas = await db.execute(
            select(func.count()).where(
                Tarefa.id_lista == lista.id,
                Tarefa.flg_ativo == True,
                Tarefa.flg_concluida == True,
            )
        )
        out.append({
            "id": lista.id,
            "nome": lista.nome,
            "cor": lista.cor,
            "icone": lista.icone,
            "ordem": lista.ordem,
            "criado_em": lista.criado_em,
            "total_tarefas": total.scalar() or 0,
            "total_concluidas": concluidas.scalar() or 0,
        })
    return out


async def criar_lista(id_usuario: uuid.UUID, dados: ListaCreate, db: AsyncSession) -> Lista:
    lista = Lista(id_usuario=id_usuario, **dados.model_dump())
    db.add(lista)
    await db.commit()
    await db.refresh(lista)
    logger.info("Lista criada | id={} nome={}", lista.id, lista.nome)
    return lista


async def atualizar_lista(
    id_lista: uuid.UUID, id_usuario: uuid.UUID, dados: ListaUpdate, db: AsyncSession
) -> Lista | None:
    result = await db.execute(
        select(Lista).where(Lista.id == id_lista, Lista.id_usuario == id_usuario, Lista.flg_ativo == True)
    )
    lista = result.scalar_one_or_none()
    if not lista:
        return None
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(lista, campo, valor)
    await db.commit()
    await db.refresh(lista)
    return lista


async def deletar_lista(id_lista: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Lista).where(Lista.id == id_lista, Lista.id_usuario == id_usuario, Lista.flg_ativo == True)
    )
    lista = result.scalar_one_or_none()
    if not lista:
        return False
    lista.flg_ativo = False
    # Soft delete das tarefas da lista
    tarefas = await db.execute(
        select(Tarefa).where(Tarefa.id_lista == id_lista, Tarefa.flg_ativo == True)
    )
    for tarefa in tarefas.scalars().all():
        tarefa.flg_ativo = False
    await db.commit()
    return True


# ─── Tarefas ──────────────────────────────────────────────────────────────────

async def listar_tarefas(
    id_usuario: uuid.UUID,
    db: AsyncSession,
    id_lista: uuid.UUID | None = None,
    concluidas: bool | None = None,
) -> list[Tarefa]:
    query = select(Tarefa).where(Tarefa.id_usuario == id_usuario, Tarefa.flg_ativo == True)
    if id_lista is not None:
        query = query.where(Tarefa.id_lista == id_lista)
    if concluidas is not None:
        query = query.where(Tarefa.flg_concluida == concluidas)
    query = query.order_by(Tarefa.flg_concluida, Tarefa.prioridade.desc(), Tarefa.ordem, Tarefa.criado_em)
    result = await db.execute(query)
    return result.scalars().all()


async def buscar_ou_criar_lista(
    nome: str | None, id_usuario: uuid.UUID, db: AsyncSession
) -> uuid.UUID | None:
    """Busca lista pelo nome (case-insensitive) ou cria uma nova. Retorna id_lista."""
    nome_efetivo = (nome or "Tarefas").strip()
    result = await db.execute(
        select(Lista).where(
            Lista.id_usuario == id_usuario,
            Lista.flg_ativo == True,
            func.lower(Lista.nome) == nome_efetivo.lower(),
        )
    )
    lista = result.scalar_one_or_none()
    if lista:
        return lista.id
    # Criar nova lista com nome fornecido
    nova_lista = Lista(id_usuario=id_usuario, nome=nome_efetivo)
    db.add(nova_lista)
    await db.flush()
    logger.info("Lista criada automaticamente via chat | nome={}", nome_efetivo)
    return nova_lista.id


async def criar_tarefa(dados: TarefaCreate, id_usuario: uuid.UUID, db: AsyncSession) -> Tarefa:
    tarefa = Tarefa(id_usuario=id_usuario, **dados.model_dump())
    db.add(tarefa)
    await db.flush()
    logger.info("Tarefa criada | id={} titulo={}", tarefa.id, tarefa.titulo)
    return tarefa


async def concluir_tarefa(
    id_tarefa: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> Tarefa | None:
    result = await db.execute(
        select(Tarefa).where(Tarefa.id == id_tarefa, Tarefa.id_usuario == id_usuario, Tarefa.flg_ativo == True)
    )
    tarefa = result.scalar_one_or_none()
    if not tarefa:
        return None
    tarefa.flg_concluida = not tarefa.flg_concluida
    tarefa.dat_concluida = datetime.now(timezone.utc) if tarefa.flg_concluida else None
    await db.commit()
    await db.refresh(tarefa)
    return tarefa


async def atualizar_tarefa(
    id_tarefa: uuid.UUID, id_usuario: uuid.UUID, dados: TarefaUpdate, db: AsyncSession
) -> Tarefa | None:
    result = await db.execute(
        select(Tarefa).where(Tarefa.id == id_tarefa, Tarefa.id_usuario == id_usuario, Tarefa.flg_ativo == True)
    )
    tarefa = result.scalar_one_or_none()
    if not tarefa:
        return None
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(tarefa, campo, valor)
    await db.commit()
    await db.refresh(tarefa)
    return tarefa


async def deletar_tarefa(id_tarefa: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Tarefa).where(Tarefa.id == id_tarefa, Tarefa.id_usuario == id_usuario, Tarefa.flg_ativo == True)
    )
    tarefa = result.scalar_one_or_none()
    if not tarefa:
        return False
    tarefa.flg_ativo = False
    await db.commit()
    return True
