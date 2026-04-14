import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.livros import service
from app.modules.livros.schemas import (
    LivroResponse,
    LeituraResponse,
    ProgressoResponse,
    ProgressoUpdate,
)

router = APIRouter()

_TAMANHO_PADRAO_CHUNK = 300   # palavras
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


# ─── Biblioteca ───────────────────────────────────────────────────────────────

@router.get("/", response_model=list[LivroResponse])
async def listar_livros(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os livros do usuario com progresso."""
    return await service.listar_livros(usuario.id, db)


@router.post("/", response_model=LivroResponse, status_code=201)
async def upload_livro(
    arquivo: UploadFile = File(...),
    titulo: str = Form(...),
    autor: str | None = Form(None),
    palavras_por_chunk: int = Form(_TAMANHO_PADRAO_CHUNK),
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Faz upload de um PDF e processa em chunks para leitura."""
    if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF sao aceitos")

    conteudo = await arquivo.read()
    if len(conteudo) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Limite: 50 MB")
    if len(conteudo) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if not (50 <= palavras_por_chunk <= 1000):
        raise HTTPException(
            status_code=422,
            detail="Tamanho do chunk deve estar entre 50 e 1000 palavras",
        )

    try:
        livro = await service.processar_upload(
            id_usuario=usuario.id,
            titulo=titulo.strip(),
            autor=autor.strip() if autor else None,
            conteudo_bytes=conteudo,
            palavras_por_chunk=palavras_por_chunk,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return livro


@router.delete("/{id_livro}", status_code=204)
async def deletar_livro(
    id_livro: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove o livro da biblioteca (soft delete)."""
    ok = await service.deletar_livro(id_livro, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Livro nao encontrado")


# ─── Leitura ──────────────────────────────────────────────────────────────────

@router.get("/{id_livro}/ler/proximo", response_model=LeituraResponse)
async def ler_proximo(
    id_livro: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o proximo trecho e avanca o ponteiro de leitura."""
    resultado = await service.ler_proximo(id_livro, usuario.id, db)
    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Livro nao encontrado ou leitura ja concluida",
        )
    return resultado


@router.get("/{id_livro}/ler/anterior", response_model=LeituraResponse)
async def ler_anterior(
    id_livro: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Volta um trecho."""
    resultado = await service.ler_anterior(id_livro, usuario.id, db)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Livro nao encontrado")
    return resultado


# ─── Configuracao ─────────────────────────────────────────────────────────────

@router.get("/{id_livro}/progresso", response_model=ProgressoResponse)
async def obter_progresso(
    id_livro: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o progresso atual de leitura."""
    livro = await service.obter_livro(id_livro, usuario.id, db)
    if not livro or not livro.progresso:
        raise HTTPException(status_code=404, detail="Livro nao encontrado")
    return livro.progresso


@router.patch("/{id_livro}/progresso", response_model=ProgressoResponse)
async def atualizar_progresso(
    id_livro: uuid.UUID,
    dados: ProgressoUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza tamanho do chunk e/ou modo estudo."""
    progresso = await service.atualizar_progresso(id_livro, usuario.id, dados, db)
    if not progresso:
        raise HTTPException(status_code=404, detail="Livro nao encontrado")
    return progresso
