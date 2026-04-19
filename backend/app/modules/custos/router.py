"""Rotas de consulta de custos de API."""

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
    except Exception as e:
        logger.error(f"Erro ao obter custos: {e}")
        raise HTTPException(
            status_code=500, detail="Erro ao consultar API de usage da OpenAI"
        )
