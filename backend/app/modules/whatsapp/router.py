"""
Rotas da integracao WhatsApp via Evolution API.

- POST /api/whatsapp/webhook    PUBLICA — valida apikey no header
- GET  /api/whatsapp/status     AUTH    — estado da integracao
- GET  /api/whatsapp/qrcode     AUTH    — QR para reconectar
- POST /api/whatsapp/reconectar AUTH    — restart da instancia

⚠️ Modo 1 NUNCA chama send_text. Nenhuma rota desse router envia mensagem.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.memoria.models import Pessoa
from app.modules.whatsapp import service
from app.modules.whatsapp.client import EvolutionAPIError, client as evolution_client
from app.modules.whatsapp.schemas import (
    EvolutionWebhookPayload,
    QrCodeResponse,
    ReconectarResponse,
    StatusResponse,
)


router = APIRouter()


# ─── Webhook (publico) ──────────────────────────────────────────────────────


@router.post("/webhook", status_code=200)
async def webhook(
    request: Request,
    apikey: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Recebe eventos da Evolution API. Sem JWT — autenticacao por apikey.

    Eventos tratados:
      - messages.upsert  -> processa mensagem recebida
      - connection.update -> apenas log

    Outros eventos sao aceitos e descartados (status 200 para a Evolution
    nao reenviar).
    """
    # Kill switch
    if not settings.whatsapp_enabled:
        logger.debug("Webhook recebido mas WHATSAPP_ENABLED=false — ignorando")
        return {"acao": "desabilitado"}

    # Validacao de apikey (constant-time)
    if not service.validar_apikey(apikey):
        client_ip = request.client.host if request.client else "?"
        logger.warning("Webhook WhatsApp com apikey invalida | ip={}", client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="apikey invalida")

    # Parse defensivo
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")

    payload = EvolutionWebhookPayload(**body) if body else EvolutionWebhookPayload()
    payload_dict = payload.model_dump()
    # Mantem o dict original (extras) — o Pydantic perde campos desconhecidos no dump
    payload_dict.update({"data": body.get("data", {})})

    evento = (payload.event or body.get("event") or "").lower().replace("_", ".")

    try:
        if evento in ("messages.upsert",):
            resultado = await service.processar_webhook_messages_upsert(payload_dict, db)
        elif evento in ("connection.update",):
            resultado = await service.processar_webhook_connection_update(payload_dict)
        else:
            resultado = {"acao": "ignorado", "evento": evento}
    except Exception as e:
        # NUNCA quebrar — Evolution reenvia em loop se retornarmos 5xx
        logger.error("Erro no processamento do webhook WhatsApp: {}", str(e))
        resultado = {"acao": "erro_interno", "evento": evento}

    return resultado


# ─── Status (com auth) ──────────────────────────────────────────────────────


@router.get("/status", response_model=StatusResponse)
async def status_integracao(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna estado da integracao + estatisticas locais."""
    state = "unknown"
    profile_name: str | None = None
    profile_picture_url: str | None = None

    if settings.whatsapp_enabled and settings.evolution_api_url:
        try:
            estado = await evolution_client.fetch_connection_state()
            # Resposta tipica: {"instance": {"instanceName": "...", "state": "open"}}
            state = (
                estado.get("instance", {}).get("state")
                or estado.get("state")
                or "unknown"
            )
        except EvolutionAPIError as e:
            logger.debug("Falha ao buscar connectionState: {}", str(e))

        try:
            info = await evolution_client.fetch_instance()
            # Resposta tipica: lista com 1 instancia
            if isinstance(info, list) and info:
                inst = info[0]
                profile_name = inst.get("profileName") or inst.get("ownerJid")
                profile_picture_url = inst.get("profilePicUrl")
        except EvolutionAPIError:
            pass

    # Contador local
    mensagens_hoje = await service.get_contador_hoje()

    # Total de pessoas monitoradas
    total_monitorados_q = await db.execute(
        select(func.count())
        .select_from(Pessoa)
        .where(
            Pessoa.id_usuario == usuario.id,
            Pessoa.flg_monitorar_whatsapp == True,  # noqa: E712
            Pessoa.flg_ativo == True,  # noqa: E712
        )
    )
    contatos_monitorados = total_monitorados_q.scalar() or 0

    # Ultima mensagem WhatsApp recebida
    from app.modules.chat.models import Conversa, Mensagem

    ultima_q = await db.execute(
        select(Mensagem.criado_em)
        .join(Conversa, Conversa.id == Mensagem.id_conversa)
        .where(
            Conversa.id_usuario == usuario.id,
            Conversa.titulo.like("WhatsApp:%"),
            Mensagem.papel == "user",
        )
        .order_by(Mensagem.criado_em.desc())
        .limit(1)
    )
    ultima_mensagem_em: datetime | None = ultima_q.scalar_one_or_none()

    return StatusResponse(
        enabled=settings.whatsapp_enabled,
        instancia=settings.evolution_instance_name or "",
        conectado=state == "open",
        state=state,
        profile_name=profile_name,
        profile_picture_url=profile_picture_url,
        mensagens_hoje=mensagens_hoje,
        ultima_mensagem_em=ultima_mensagem_em,
        contatos_monitorados=contatos_monitorados,
    )


# ─── QR Code (com auth) ─────────────────────────────────────────────────────


@router.get("/qrcode", response_model=QrCodeResponse)
async def get_qrcode(usuario: Usuario = Depends(get_current_user)):
    """Retorna QR Code para reconectar a instancia."""
    if not settings.whatsapp_enabled or not settings.evolution_api_url:
        raise HTTPException(status_code=503, detail="WhatsApp desabilitado")

    try:
        resp = await evolution_client.connect_instance()
    except EvolutionAPIError as e:
        raise HTTPException(status_code=502, detail=f"Evolution: {e}")

    qrcode_b64 = (
        resp.get("base64")
        or resp.get("qrcode", {}).get("base64")
        or None
    )
    code = (
        resp.get("code")
        or resp.get("qrcode", {}).get("code")
        or None
    )
    state = resp.get("instance", {}).get("state") or resp.get("state") or "unknown"

    return QrCodeResponse(qrcode_base64=qrcode_b64, code=code, state=state)


# ─── Reconectar (com auth) ──────────────────────────────────────────────────


@router.post("/reconectar", response_model=ReconectarResponse)
async def reconectar(usuario: Usuario = Depends(get_current_user)):
    """Forca restart da instancia Evolution."""
    if not settings.whatsapp_enabled or not settings.evolution_api_url:
        raise HTTPException(status_code=503, detail="WhatsApp desabilitado")

    try:
        resp = await evolution_client.restart_instance()
        state = resp.get("instance", {}).get("state") or resp.get("state") or "unknown"
        return ReconectarResponse(sucesso=True, state=state, mensagem="Restart enviado")
    except EvolutionAPIError as e:
        return ReconectarResponse(sucesso=False, state="unknown", mensagem=str(e))
