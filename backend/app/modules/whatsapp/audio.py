"""
Download de audio do WhatsApp via Evolution + transcricao com Whisper-1.

Evolution v2 expoe POST /chat/getBase64FromMediaMessage/{instance} que retorna
o conteudo da midia em base64. Convertemos para bytes e mandamos pro Whisper.
"""

import base64
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.modules.ia.service import transcrever_audio


# Whisper-1 limite oficial: 25MB
LIMITE_AUDIO_BYTES = 25 * 1024 * 1024


async def baixar_audio_da_evolution(message_payload: dict[str, Any]) -> bytes | None:
    """
    Baixa o conteudo binario de uma mensagem de audio.

    Recebe o payload completo de uma mensagem (chave 'message' do MESSAGES_UPSERT)
    e retorna os bytes do audio, ou None em caso de falha.
    """
    if not settings.evolution_api_url or not settings.evolution_api_key:
        return None

    base_url = settings.evolution_api_url.rstrip("/")
    instance = settings.evolution_instance_name
    url = f"{base_url}/chat/getBase64FromMediaMessage/{instance}"

    headers = {
        "apikey": settings.evolution_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "message": message_payload,
        "convertToMp4": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as cli:
            resp = await cli.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.warning(
                "Falha ao baixar audio | status={} | corpo={}",
                resp.status_code, resp.text[:200],
            )
            return None
        data = resp.json()
        b64 = data.get("base64") or data.get("data") or ""
        if not b64:
            logger.warning("Resposta sem base64 da Evolution: {}", data)
            return None
        audio_bytes = base64.b64decode(b64)
        if len(audio_bytes) > LIMITE_AUDIO_BYTES:
            logger.warning("Audio excede 25MB | tamanho={}", len(audio_bytes))
            return None
        return audio_bytes
    except Exception as e:
        logger.warning("Erro ao baixar audio da Evolution: {}", str(e))
        return None


async def transcrever_audio_whatsapp(message_payload: dict[str, Any]) -> str | None:
    """
    Baixa o audio + transcreve via Whisper.
    Retorna o texto transcrito ou None se falhar.
    """
    audio_bytes = await baixar_audio_da_evolution(message_payload)
    if not audio_bytes:
        return None
    try:
        # Evolution sempre entrega audio em ogg/opus do Baileys
        return await transcrever_audio(audio_bytes, filename="audio.ogg")
    except Exception as e:
        logger.warning("Falha ao transcrever audio WhatsApp: {}", str(e))
        return None
