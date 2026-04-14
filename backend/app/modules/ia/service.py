"""
Modulo IA — Orquestrador de modelos de linguagem.

Regras:
- Claude (claude-sonnet-4-6): raciocinio, conversas complexas, contexto longo
- GPT-4o mini: tarefas simples (titulo de conversa, classificacao) e fallback do Claude
- Fallback automatico: se Claude falhar (5xx/timeout), tenta GPT-4o mini automaticamente
"""

from collections.abc import AsyncGenerator

import anthropic
import httpx
from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.modules.ia.prompts import LEMBRETE_PARSE_PROMPT, SYSTEM_PROMPT, TAREFA_PARSE_PROMPT, TITULO_PROMPT

# Clientes de IA (instanciados uma vez)
_claude_client: anthropic.AsyncAnthropic | None = None
_openai_client: AsyncOpenAI | None = None


def get_claude() -> anthropic.AsyncAnthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _claude_client


def get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def gerar_resposta_stream(
    mensagens: list[dict],
    contexto_memoria: str = "",
) -> AsyncGenerator[tuple[str, str, int, int], None]:
    """
    Gera resposta do Jarvis via streaming.

    Yields: (chunk_texto, modelo_usado, tokens_entrada, tokens_saida)
    - tokens_entrada e tokens_saida so sao preenchidos no ultimo chunk (chunk vazio)

    Tenta Claude primeiro, faz fallback para GPT-4o mini em caso de erro.
    """
    system = SYSTEM_PROMPT
    if contexto_memoria:
        system += f"\n\nContexto de memoria relevante:\n{contexto_memoria}"

    # Tentar Claude primeiro
    try:
        async for chunk in _stream_claude(mensagens, system):
            yield chunk
        return
    except (anthropic.APIStatusError, anthropic.APIConnectionError, httpx.TimeoutException) as e:
        logger.warning("Claude falhou, ativando fallback GPT-4o mini | erro={}", str(e))

    # Fallback: GPT-4o mini
    async for chunk in _stream_openai(mensagens, system):
        yield chunk


async def _stream_claude(
    mensagens: list[dict], system: str
) -> AsyncGenerator[tuple[str, str, int, int], None]:
    """Streaming via Claude API."""
    cliente = get_claude()
    tokens_entrada = 0
    tokens_saida = 0
    modelo = "claude-sonnet-4-6"

    async with cliente.messages.stream(
        model=modelo,
        max_tokens=4096,
        system=system,
        messages=mensagens,
    ) as stream:
        async for texto in stream.text_stream:
            yield (texto, modelo, 0, 0)

        # Obter uso de tokens no final
        msg_final = await stream.get_final_message()
        tokens_entrada = msg_final.usage.input_tokens
        tokens_saida = msg_final.usage.output_tokens

    # Chunk final vazio com tokens preenchidos
    yield ("", modelo, tokens_entrada, tokens_saida)


async def _stream_openai(
    mensagens: list[dict], system: str
) -> AsyncGenerator[tuple[str, str, int, int], None]:
    """Streaming via OpenAI GPT-4o (fallback)."""
    cliente = get_openai()
    modelo = "gpt-4o"
    tokens_entrada = 0
    tokens_saida = 0

    # Formatar mensagens com system prompt para OpenAI
    msgs_openai = [{"role": "system", "content": system}] + mensagens

    stream = await cliente.chat.completions.create(
        model=modelo,
        messages=msgs_openai,
        max_tokens=4096,
        stream=True,
        stream_options={"include_usage": True},
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield (chunk.choices[0].delta.content, modelo, 0, 0)
        # Ultimo chunk tem usage
        if chunk.usage:
            tokens_entrada = chunk.usage.prompt_tokens
            tokens_saida = chunk.usage.completion_tokens

    yield ("", modelo, tokens_entrada, tokens_saida)


async def gerar_titulo(primeira_mensagem: str) -> str:
    """Gera titulo curto para a conversa usando GPT-4o."""
    try:
        cliente = get_openai()
        response = await cliente.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": TITULO_PROMPT.format(mensagem=primeira_mensagem[:500]),
                }
            ],
            max_tokens=20,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Falha ao gerar titulo: {}", str(e))
        return "Nova conversa"


async def detectar_lembrete(mensagem: str) -> dict | None:
    """
    Detecta se a mensagem e um pedido de lembrete e retorna os dados parseados.
    Retorna None se nao for um pedido de lembrete.
    """
    import json
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        import re
        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        cliente = get_openai()
        response = await cliente.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": LEMBRETE_PARSE_PROMPT.format(agora=agora, mensagem=mensagem[:500]),
                }
            ],
            max_tokens=200,
            temperature=0,
            response_format={"type": "json_object"},
        )
        texto = response.choices[0].message.content.strip()
        if not texto:
            return None
        # Extrair JSON mesmo se vier com texto em volta
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if not match:
            return None
        dados = json.loads(match.group())
        if dados.get("eh_lembrete"):
            return dados
        return None
    except Exception as e:
        logger.warning("Falha ao detectar lembrete: {}", str(e))
        return None


async def detectar_tarefa(mensagem: str) -> dict | None:
    """
    Detecta se a mensagem e um pedido de criacao de tarefa e retorna os dados parseados.
    Retorna None se nao for um pedido de tarefa.
    """
    import json
    import re
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        cliente = get_openai()
        response = await cliente.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": TAREFA_PARSE_PROMPT.format(agora=agora, mensagem=mensagem[:500]),
                }
            ],
            max_tokens=200,
            temperature=0,
            response_format={"type": "json_object"},
        )
        texto = response.choices[0].message.content.strip()
        if not texto:
            return None
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if not match:
            return None
        dados = json.loads(match.group())
        if dados.get("eh_tarefa"):
            return dados
        return None
    except Exception as e:
        logger.warning("Falha ao detectar tarefa: {}", str(e))
        return None


async def transcrever_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcreve audio via OpenAI Whisper.
    Retorna o texto transcrito.
    """
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
        input=texto[:8000],  # Limite de tokens
    )
    return response.data[0].embedding
