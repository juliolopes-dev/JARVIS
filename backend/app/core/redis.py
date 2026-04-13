import redis.asyncio as aioredis

from app.core.config import settings

# Pool de conexoes Redis
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Retorna conexao Redis do pool. Cria pool na primeira chamada."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def fechar_redis() -> None:
    """Fecha o pool Redis. Chamado no shutdown da aplicacao."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


# Helpers para contexto de conversa
async def salvar_contexto(conversa_id: str, mensagens: list[dict], ttl: int = 3600) -> None:
    """Salva historico recente da conversa no Redis (TTL: 1h por padrao)."""
    import json
    r = await get_redis()
    await r.setex(f"contexto:{conversa_id}", ttl, json.dumps(mensagens, ensure_ascii=False))


async def buscar_contexto(conversa_id: str) -> list[dict]:
    """Busca historico recente da conversa no Redis. Retorna lista vazia se nao existir."""
    import json
    r = await get_redis()
    dados = await r.get(f"contexto:{conversa_id}")
    return json.loads(dados) if dados else []


async def limpar_contexto(conversa_id: str) -> None:
    """Remove contexto da conversa do Redis."""
    r = await get_redis()
    await r.delete(f"contexto:{conversa_id}")
