from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.middleware.rate_limit import limiter
from app.modules.auth import service
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import (
    AlterarSenhaRequest,
    LoginRequest,
    RefreshRequest,
    RegistrarRequest,
    TokenResponse,
    UsuarioResponse,
)

router = APIRouter()


@router.post("/registrar", response_model=UsuarioResponse, status_code=201)
async def registrar(dados: RegistrarRequest, db: AsyncSession = Depends(get_db)):
    """Cria conta (uso unico — setup inicial)."""
    try:
        usuario = await service.registrar_usuario(dados, db)
        return usuario
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    dados: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login → retorna JWT de acesso e refresh token."""
    from loguru import logger

    resultado = await service.autenticar_usuario(dados, db)
    if not resultado:
        # Logar tentativa falha com IP — nunca logar a senha
        logger.warning(
            "Login falhou | email={} | ip={}",
            dados.email,
            request.client.host if request.client else "desconhecido",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    access_token, refresh_token = resultado
    logger.info(
        "Login ok | email={} | ip={}",
        dados.email,
        request.client.host if request.client else "desconhecido",
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(dados: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Renova JWT com refresh token."""
    resultado = await service.renovar_token(dados.refresh_token, db)
    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado",
        )
    access_token, refresh_token = resultado
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UsuarioResponse)
async def me(usuario: Usuario = Depends(get_current_user)):
    """Retorna dados do usuario logado."""
    return usuario


@router.put("/senha")
async def alterar_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Altera senha do usuario logado."""
    ok = await service.alterar_senha(usuario, dados.senha_atual, dados.nova_senha, db)
    if not ok:
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    return {"success": True, "message": "Senha alterada com sucesso"}
