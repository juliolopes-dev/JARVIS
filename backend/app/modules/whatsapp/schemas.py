"""
Schemas Pydantic para o modulo WhatsApp Modo 1 (Observador).

Cobrem:
- Payloads recebidos da Evolution API v2 (webhook MESSAGES_UPSERT, CONNECTION_UPDATE)
- Respostas das rotas /api/whatsapp/* (status, qrcode)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Webhook Evolution → Jarvis ─────────────────────────────────────────────


class EvolutionMessageKey(BaseModel):
    """Chave da mensagem no payload da Evolution."""
    remoteJid: str = ""
    fromMe: bool = False
    id: str = ""
    participant: str | None = None  # presente em mensagens de grupo


class EvolutionWebhookPayload(BaseModel):
    """
    Payload generico que a Evolution envia para o webhook global.
    Apenas campos usados pelo Modo 1 — outros sao ignorados (extra="allow").
    """
    event: str = ""               # "messages.upsert" | "connection.update" | etc
    instance: str = ""            # nome da instancia (ex: "juliolopes")
    data: dict[str, Any] = Field(default_factory=dict)
    apikey: str | None = None     # token da instancia (validacao adicional)
    server_url: str | None = None
    date_time: str | None = None

    model_config = {"extra": "allow"}


# ─── Respostas das rotas /api/whatsapp/* ────────────────────────────────────


class StatusResponse(BaseModel):
    """Estado atual da integracao com a Evolution + estatisticas locais."""
    enabled: bool                          # WHATSAPP_ENABLED
    instancia: str                         # nome da instancia configurada
    conectado: bool                        # state == "open"
    state: str                             # "open" | "close" | "connecting" | "unknown"
    profile_name: str | None = None        # nome do perfil WhatsApp conectado
    profile_picture_url: str | None = None
    mensagens_hoje: int = 0                # total processadas hoje (BRT)
    ultima_mensagem_em: datetime | None = None
    contatos_monitorados: int = 0          # pessoas com flg_monitorar_whatsapp=true


class QrCodeResponse(BaseModel):
    """QR Code para escanear com o WhatsApp."""
    qrcode_base64: str | None = None       # data:image/png;base64,... ou string base64
    code: str | None = None                # codigo de pareamento textual (se disponivel)
    state: str = "unknown"


class ReconectarResponse(BaseModel):
    """Resposta apos forcar reconexao da instancia."""
    sucesso: bool
    state: str = "unknown"
    mensagem: str = ""
