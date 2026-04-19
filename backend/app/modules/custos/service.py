"""
Servico de consulta de custos/usage da OpenAI.

Le a API oficial /v1/organization/usage/* com admin key e converte tokens
em USD usando tabela de precos hardcoded (atualizar manualmente quando mudar).

Cache em memoria de 15 minutos — usage da OpenAI nao atualiza em tempo
real mesmo, nao faz sentido consultar a cada request.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings

# Precos em USD por 1M tokens (atualizar conforme mudar na OpenAI)
# Referencia: https://openai.com/api/pricing/
PRECOS_USD_POR_MILHAO = {
    # Chat / completions
    "gpt-4o": {"input": 2.50, "output": 10.00, "cached_input": 1.25},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00, "cached_input": 1.25},
    "gpt-4o-2024-11-20": {"input": 2.50, "output": 10.00, "cached_input": 1.25},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cached_input": 0.075},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60, "cached_input": 0.075},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Embeddings
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
}

# Precos especiais nao baseados em tokens
PRECO_WHISPER_USD_POR_MINUTO = 0.006
PRECO_TTS_USD_POR_MILHAO_CARS = 15.00  # tts-1
PRECO_TTS_HD_USD_POR_MILHAO_CARS = 30.00  # tts-1-hd

# Cache simples: {chave: (timestamp, dados)}
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SEGUNDOS = 15 * 60  # 15 minutos


def _preco_por_modelo(modelo: str, tokens_input: int, tokens_output: int, cached: int = 0) -> float:
    """Calcula custo USD para um modelo. Retorna 0 se modelo desconhecido."""
    preco = PRECOS_USD_POR_MILHAO.get(modelo)
    if not preco:
        # Tenta match parcial (gpt-4o-2024-11-20 -> gpt-4o)
        for chave, val in PRECOS_USD_POR_MILHAO.items():
            if modelo.startswith(chave):
                preco = val
                break
    if not preco:
        logger.warning(f"Preco desconhecido para modelo: {modelo}")
        return 0.0

    input_nao_cached = max(0, tokens_input - cached)
    custo = (input_nao_cached / 1_000_000) * preco["input"]
    custo += (tokens_output / 1_000_000) * preco["output"]
    if cached and "cached_input" in preco:
        custo += (cached / 1_000_000) * preco["cached_input"]
    return custo


async def _obter_cotacao_usd_brl() -> float:
    """Busca cotacao USD->BRL via awesomeapi (gratuita, sem chave).
    Fallback: 5.00 se API falhar.
    """
    chave = "cotacao_usd_brl"
    if chave in _CACHE:
        ts, val = _CACHE[chave]
        if time.time() - ts < 3600:  # cache cotacao por 1h
            return val
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://economia.awesomeapi.com.br/last/USD-BRL")
            r.raise_for_status()
            dados = r.json()
            cotacao = float(dados["USDBRL"]["bid"])
            _CACHE[chave] = (time.time(), cotacao)
            return cotacao
    except Exception as e:
        logger.warning(f"Falha ao buscar cotacao USD-BRL: {e}")
        return 5.00


async def _chamar_usage_api(
    endpoint: str, start_unix: int, end_unix: int, bucket_width: str = "1d"
) -> list[dict]:
    """Chama um endpoint de /v1/organization/usage/* e retorna os buckets.
    Lida com paginacao via next_page.
    """
    if not settings.openai_admin_key:
        raise ValueError(
            "OPENAI_ADMIN_KEY nao configurada. Pegar em "
            "https://platform.openai.com/settings/organization/admin-keys"
        )

    url = f"https://api.openai.com/v1/organization/usage/{endpoint}"
    headers = {"Authorization": f"Bearer {settings.openai_admin_key}"}
    params: dict[str, Any] = {
        "start_time": start_unix,
        "end_time": end_unix,
        "bucket_width": bucket_width,
        "group_by": ["model"],
        "limit": 31,
    }

    todos_buckets: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            r = await client.get(url, headers=headers, params=params)
            if r.status_code == 401:
                raise ValueError("OPENAI_ADMIN_KEY invalida ou sem permissao.")
            if r.status_code >= 400:
                logger.error(
                    f"OpenAI Usage API {endpoint} retornou {r.status_code}: {r.text[:500]}"
                )
            r.raise_for_status()
            dados = r.json()
            todos_buckets.extend(dados.get("data", []))
            if not dados.get("has_more"):
                break
            params["page"] = dados.get("next_page")
            if not params["page"]:
                break
    return todos_buckets


async def obter_resumo_custos(periodo: str = "mes_atual") -> dict[str, Any]:
    """Retorna resumo consolidado de custos no periodo.

    periodo: 'mes_atual' | 'mes_anterior' | 'ultimos_7_dias' | 'ultimos_30_dias'
    """
    chave_cache = f"resumo_{periodo}"
    if chave_cache in _CACHE:
        ts, val = _CACHE[chave_cache]
        if time.time() - ts < _CACHE_TTL_SEGUNDOS:
            return val

    agora = datetime.now(timezone.utc)
    if periodo == "mes_atual":
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fim = agora
    elif periodo == "mes_anterior":
        primeiro_dia_mes_atual = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fim = primeiro_dia_mes_atual
        # Primeiro dia do mes anterior
        if primeiro_dia_mes_atual.month == 1:
            inicio = primeiro_dia_mes_atual.replace(
                year=primeiro_dia_mes_atual.year - 1, month=12
            )
        else:
            inicio = primeiro_dia_mes_atual.replace(month=primeiro_dia_mes_atual.month - 1)
    elif periodo == "ultimos_7_dias":
        inicio = agora - timedelta(days=7)
        fim = agora
    elif periodo == "ultimos_30_dias":
        inicio = agora - timedelta(days=30)
        fim = agora
    else:
        raise ValueError(f"Periodo invalido: {periodo}")

    start_unix = int(inicio.timestamp())
    end_unix = int(fim.timestamp())

    # 1. Completions (chat)
    buckets_completions = await _chamar_usage_api("completions", start_unix, end_unix)

    # 2. Embeddings
    try:
        buckets_embeddings = await _chamar_usage_api("embeddings", start_unix, end_unix)
    except Exception as e:
        logger.warning(f"Falha ao buscar embeddings usage: {e}")
        buckets_embeddings = []

    # 3. Audio (Whisper)
    try:
        buckets_audio = await _chamar_usage_api(
            "audio_transcriptions", start_unix, end_unix
        )
    except Exception as e:
        logger.warning(f"Falha ao buscar audio usage: {e}")
        buckets_audio = []

    # Agregar por modelo e por dia
    por_modelo: dict[str, dict] = {}
    por_dia: dict[str, float] = {}
    total_usd = 0.0

    for bucket in buckets_completions + buckets_embeddings:
        dia_iso = datetime.fromtimestamp(bucket["start_time"], tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
        for resultado in bucket.get("results", []):
            modelo = resultado.get("model") or "desconhecido"
            tokens_in = resultado.get("input_tokens", 0)
            tokens_out = resultado.get("output_tokens", 0)
            cached = resultado.get("input_cached_tokens", 0)
            custo = _preco_por_modelo(modelo, tokens_in, tokens_out, cached)
            total_usd += custo
            por_dia[dia_iso] = por_dia.get(dia_iso, 0.0) + custo
            if modelo not in por_modelo:
                por_modelo[modelo] = {
                    "modelo": modelo,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "custo_usd": 0.0,
                }
            por_modelo[modelo]["tokens_in"] += tokens_in
            por_modelo[modelo]["tokens_out"] += tokens_out
            por_modelo[modelo]["custo_usd"] += custo

    # Whisper — cobrado por segundos de audio
    for bucket in buckets_audio:
        dia_iso = datetime.fromtimestamp(bucket["start_time"], tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
        for resultado in bucket.get("results", []):
            modelo = resultado.get("model") or "whisper-1"
            segundos = resultado.get("seconds", 0)
            minutos = segundos / 60.0
            custo = minutos * PRECO_WHISPER_USD_POR_MINUTO
            total_usd += custo
            por_dia[dia_iso] = por_dia.get(dia_iso, 0.0) + custo
            chave_m = f"{modelo} (audio)"
            if chave_m not in por_modelo:
                por_modelo[chave_m] = {
                    "modelo": chave_m,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "custo_usd": 0.0,
                    "segundos_audio": 0,
                }
            por_modelo[chave_m]["segundos_audio"] = (
                por_modelo[chave_m].get("segundos_audio", 0) + segundos
            )
            por_modelo[chave_m]["custo_usd"] += custo

    cotacao = await _obter_cotacao_usd_brl()

    lista_por_dia = [
        {"dia": d, "custo_usd": round(v, 4), "custo_brl": round(v * cotacao, 2)}
        for d, v in sorted(por_dia.items())
    ]
    lista_por_modelo = sorted(
        [
            {
                **dados,
                "custo_usd": round(dados["custo_usd"], 4),
                "custo_brl": round(dados["custo_usd"] * cotacao, 2),
            }
            for dados in por_modelo.values()
        ],
        key=lambda x: x["custo_usd"],
        reverse=True,
    )

    resultado = {
        "periodo": periodo,
        "dat_inicio": inicio.isoformat(),
        "dat_fim": fim.isoformat(),
        "total_usd": round(total_usd, 4),
        "total_brl": round(total_usd * cotacao, 2),
        "cotacao_usd_brl": round(cotacao, 4),
        "por_modelo": lista_por_modelo,
        "por_dia": lista_por_dia,
    }

    _CACHE[chave_cache] = (time.time(), resultado)
    return resultado
