from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import Usuario
from app.modules.config import service
from app.modules.config.schemas import ConfiguracaoResponse, ConfiguracaoUpdate

router = APIRouter()


def _config_para_response(config) -> dict:
    return {
        "id": config.id,
        "modelo_preferido": config.modelo_preferido,
        "tema": config.tema,
        "flg_briefing_diario": config.flg_briefing_diario,
        "horario_briefing": config.horario_briefing.strftime("%H:%M"),
        "flg_notificacoes": config.flg_notificacoes,
        "criado_em": config.criado_em,
        "atualizado_em": config.atualizado_em,
    }


@router.get("", summary="Obter configuracoes do usuario")
async def obter_config(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await service.obter_ou_criar_config(usuario.id, db)
    return _config_para_response(config)


@router.put("", summary="Atualizar configuracoes do usuario")
async def atualizar_config(
    dados: ConfiguracaoUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await service.atualizar_config(usuario.id, dados, db)
    return _config_para_response(config)
