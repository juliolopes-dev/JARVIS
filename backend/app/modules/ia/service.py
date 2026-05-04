"""
Modulo IA — Orquestrador de modelos de linguagem.

Regras:
- DeepSeek v4-pro (thinking ON):  cerebro principal — conversas e raciocinio
- DeepSeek v4-pro (thinking OFF): parsers NLP e titulo — classificacao simples
- OpenAI Whisper-1:               transcricao de audio
- OpenAI text-embedding-3-small:  embeddings semanticos (1536 dim)
"""

import json
import re
from collections.abc import AsyncGenerator
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.modules.ia.prompts import (
    EVENTO_PARSE_PROMPT,
    LEMBRETE_PARSE_PROMPT,
    SYSTEM_PROMPT,
    TAREFA_PARSE_PROMPT,
    TAREFA_RECORRENTE_PARSE_PROMPT,
    TITULO_PROMPT,
)

# ── Clientes (singletons) ────────────────────────────────────────────────────

_deepseek_client: AsyncOpenAI | None = None
_openai_client: AsyncOpenAI | None = None


def get_deepseek() -> AsyncOpenAI:
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
    return _deepseek_client


def get_openai() -> AsyncOpenAI:
    """OpenAI usado apenas para Whisper e embeddings."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


# ── Helpers internos ─────────────────────────────────────────────────────────

def _agora_brt() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def _extrair_json(texto: str) -> dict:
    """Extrai JSON de resposta que pode vir com markdown ou texto extra."""
    if not texto:
        raise ValueError("resposta vazia")
    texto = texto.strip()
    if "```" in texto:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
        if match:
            texto = match.group(1)
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio != -1 and fim != -1:
        texto = texto[inicio:fim + 1]
    return json.loads(texto)


async def _chamar_parser(prompt: str, max_tokens: int = 300) -> dict:
    """DeepSeek v4-pro sem thinking para classificacao NLP — rapido e deterministico."""
    cliente = get_deepseek()
    response = await cliente.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return _extrair_json(response.choices[0].message.content or "")


# ── Cerebro principal — streaming ────────────────────────────────────────────

async def gerar_resposta_stream(
    mensagens: list[dict],
    contexto_memoria: str = "",
) -> AsyncGenerator[tuple[str, str, int, int], None]:
    """
    Gera resposta do Jarvis via streaming com DeepSeek v4-pro (thinking ativo).

    Yields: (chunk_texto, modelo_usado, tokens_entrada, tokens_saida)
    - tokens sao preenchidos apenas no ultimo chunk (chunk_texto vazio)
    - thinking tokens sao filtrados — usuario ve apenas a resposta final
    """
    system = SYSTEM_PROMPT
    if contexto_memoria:
        system += f"\n\nContexto de memoria relevante:\n{contexto_memoria}"

    async for chunk in _stream_deepseek(mensagens, system):
        yield chunk


async def _stream_deepseek(
    mensagens: list[dict], system: str
) -> AsyncGenerator[tuple[str, str, int, int], None]:
    """Streaming via DeepSeek v4-pro com thinking — ignora delta.reasoning_content."""
    cliente = get_deepseek()
    modelo = "deepseek-v4-pro"
    tokens_entrada = 0
    tokens_saida = 0

    msgs = [{"role": "system", "content": system}] + mensagens

    stream = await cliente.chat.completions.create(
        model=modelo,
        messages=msgs,
        max_tokens=4096,
        stream=True,
        stream_options={"include_usage": True},
    )

    async for chunk in stream:
        # delta.content = resposta final; delta.reasoning_content = thinking (ignorado)
        if chunk.choices and chunk.choices[0].delta.content:
            yield (chunk.choices[0].delta.content, modelo, 0, 0)
        if chunk.usage:
            tokens_entrada = chunk.usage.prompt_tokens
            tokens_saida = chunk.usage.completion_tokens

    yield ("", modelo, tokens_entrada, tokens_saida)


# ── Titulo de conversa ───────────────────────────────────────────────────────

async def gerar_titulo(primeira_mensagem: str) -> str:
    """Gera titulo curto para a conversa usando DeepSeek v4-pro (sem thinking)."""
    try:
        cliente = get_deepseek()
        response = await cliente.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {
                    "role": "user",
                    "content": TITULO_PROMPT.format(mensagem=primeira_mensagem[:500]),
                }
            ],
            max_tokens=20,
            temperature=0.3,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return (response.choices[0].message.content or "Nova conversa").strip()
    except Exception as e:
        logger.warning("Falha ao gerar titulo: {}", str(e))
        return "Nova conversa"


# ── Parsers NLP ──────────────────────────────────────────────────────────────

async def detectar_lembrete(mensagem: str) -> dict | None:
    """Detecta pedido de lembrete pontual. Retorna dados parseados ou None."""
    try:
        prompt = LEMBRETE_PARSE_PROMPT.format(agora=_agora_brt(), mensagem=mensagem[:500])
        dados = await _chamar_parser(prompt, max_tokens=200)
        return dados if dados.get("eh_lembrete") else None
    except Exception as e:
        logger.warning("Falha ao detectar lembrete: {}", str(e))
        return None


async def detectar_tarefa(mensagem: str) -> dict | None:
    """Detecta pedido de criacao de tarefa/checklist. Retorna dados parseados ou None."""
    try:
        prompt = TAREFA_PARSE_PROMPT.format(agora=_agora_brt(), mensagem=mensagem[:500])
        dados = await _chamar_parser(prompt, max_tokens=200)
        return dados if dados.get("eh_tarefa") else None
    except Exception as e:
        logger.warning("Falha ao detectar tarefa: {}", str(e))
        return None


async def detectar_tarefa_recorrente(mensagem: str) -> dict | None:
    """Detecta pedido de tarefa recorrente (cron). Retorna dados parseados ou None."""
    try:
        prompt = TAREFA_RECORRENTE_PARSE_PROMPT.format(agora=_agora_brt(), mensagem=mensagem[:500])
        dados = await _chamar_parser(prompt, max_tokens=200)
        return dados if dados.get("eh_recorrente") else None
    except Exception as e:
        logger.warning("Falha ao detectar tarefa recorrente: {}", str(e))
        return None


async def detectar_evento(mensagem: str) -> dict | None:
    """Detecta relato de evento (memoria episodica). Retorna dados parseados ou None."""
    try:
        prompt = EVENTO_PARSE_PROMPT.format(agora=_agora_brt(), mensagem=mensagem[:500])
        dados = await _chamar_parser(prompt, max_tokens=400)
        return dados if dados.get("eh_evento") else None
    except Exception as e:
        logger.warning("Falha ao detectar evento: {}", str(e))
        return None


# ── Audio e embeddings (OpenAI) ──────────────────────────────────────────────

async def transcrever_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcreve audio via OpenAI Whisper-1."""
    import io
    cliente = get_openai()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename
    try:
        response = await cliente.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="pt",
        )
        texto = response.text.strip()
        logger.info("Audio transcrito | chars={}", len(texto))
        return texto
    except Exception as e:
        logger.error("Falha ao transcrever audio: {}", str(e))
        raise


async def gerar_embedding(texto: str) -> list[float]:
    """Gera embedding via OpenAI text-embedding-3-small (1536 dim)."""
    cliente = get_openai()
    response = await cliente.embeddings.create(
        model="text-embedding-3-small",
        input=texto[:8000],
    )
    return response.data[0].embedding
