import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.chat import service
from app.modules.ia import service as ia_service
from app.modules.chat.schemas import (
    ConversaCreate,
    ConversaResponse,
    MensagemCreate,
    MensagemResponse,
)

router = APIRouter()


@router.post("/conversas", response_model=ConversaResponse, status_code=201)
async def criar_conversa(
    dados: ConversaCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inicia uma nova conversa."""
    conversa = await service.criar_conversa(usuario.id, dados.titulo, db)
    return conversa


@router.get("/conversas", response_model=list[ConversaResponse])
async def listar_conversas(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista conversas ativas do usuario."""
    return await service.listar_conversas(usuario.id, db, pagina, por_pagina)


@router.get("/conversas/{id_conversa}", response_model=ConversaResponse)
async def buscar_conversa(
    id_conversa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de uma conversa."""
    conversa = await service.buscar_conversa(id_conversa, usuario.id, db)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    return conversa


@router.delete("/conversas/{id_conversa}")
async def arquivar_conversa(
    id_conversa: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Arquiva uma conversa (soft delete)."""
    ok = await service.arquivar_conversa(id_conversa, usuario.id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    return {"success": True}


@router.post("/conversas/{id_conversa}/mensagens")
async def enviar_mensagem(
    id_conversa: uuid.UUID,
    dados: MensagemCreate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Envia mensagem e recebe resposta do Jarvis via Server-Sent Events (SSE).
    O cliente deve consumir o stream de eventos.
    """
    # Verificar se a conversa pertence ao usuario
    conversa = await service.buscar_conversa(id_conversa, usuario.id, db)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")

    return StreamingResponse(
        service.enviar_mensagem_stream(id_conversa, usuario.id, dados.conteudo, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Desabilita buffering no nginx
        },
    )


@router.get("/conversas/{id_conversa}/mensagens", response_model=list[MensagemResponse])
async def listar_mensagens(
    id_conversa: uuid.UUID,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=100),
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Historico de mensagens de uma conversa."""
    conversa = await service.buscar_conversa(id_conversa, usuario.id, db)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    return await service.listar_mensagens(id_conversa, db, pagina, por_pagina)


@router.post("/transcrever")
async def transcrever_audio(
    audio: UploadFile = File(...),
    usuario: Usuario = Depends(get_current_user),
):
    """Transcreve audio via Whisper e retorna o texto."""
    if audio.size and audio.size > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio muito grande (max 25MB)")
    conteudo = await audio.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Audio vazio")
    texto = await ia_service.transcrever_audio(conteudo, audio.filename or "audio.webm")
    if not texto:
        raise HTTPException(status_code=422, detail="Nao foi possivel transcrever o audio")
    return {"texto": texto}
