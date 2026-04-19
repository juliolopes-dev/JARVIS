"""Rotas de consulta de custos de API."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.custos import service

router = APIRouter(prefix="/custos", tags=["custos"])


@router.get("/resumo")
async def obter_resumo(
    periodo: str = Query(
        "mes_atual",
        pattern="^(mes_atual|mes_anterior|ultimos_7_dias|ultimos_30_dias)$",
    ),
    _usuario: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna resumo consolidado de custos no periodo.

    periodo:
    - mes_atual: desde o dia 1 do mes corrente
    - mes_anterior: mes calendario anterior completo
    - ultimos_7_dias: ultimos 7 dias (rolling)
    - ultimos_30_dias: ultimos 30 dias (rolling)
    """
    try:
        return await service.obter_resumo_custos(periodo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as e:
        corpo = e.response.text[:500] if e.response is not None else ""
        logger.error(f"OpenAI Usage API {e.response.status_code}: {corpo}")
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI respondeu {e.response.status_code}: {corpo}",
        )
    except Exception as e:
        logger.exception("Erro ao obter custos")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
