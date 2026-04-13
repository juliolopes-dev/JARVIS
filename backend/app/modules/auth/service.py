from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import LoginRequest, RegistrarRequest


async def registrar_usuario(dados: RegistrarRequest, db: AsyncSession) -> Usuario:
    """Cria novo usuario. Levanta ValueError se email ja existe."""
    # Verificar se email ja esta em uso
    result = await db.execute(select(Usuario).where(Usuario.email == dados.email))
    if result.scalar_one_or_none():
        raise ValueError("Email ja cadastrado")

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
    )
    db.add(usuario)
    await db.flush()  # Para obter o id gerado
    return usuario


async def autenticar_usuario(
    dados: LoginRequest, db: AsyncSession
) -> tuple[str, str] | None:
    """Autentica usuario e retorna (access_token, refresh_token) ou None se falhar."""
    result = await db.execute(
        select(Usuario).where(
            Usuario.email == dados.email,
            Usuario.flg_ativo == True,  # noqa: E712
        )
    )
    usuario = result.scalar_one_or_none()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        return None

    payload = {"sub": str(usuario.id)}
    access_token = criar_access_token(payload)
    refresh_token = criar_refresh_token(payload)
    return access_token, refresh_token


async def renovar_token(
    refresh_token: str, db: AsyncSession
) -> tuple[str, str] | None:
    """Valida refresh token e emite novos tokens. Retorna None se invalido."""
    import uuid

    payload = decodificar_token(refresh_token)
    if not payload or payload.get("tipo") != "refresh":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(
        select(Usuario).where(
            Usuario.id == uuid.UUID(user_id),
            Usuario.flg_ativo == True,  # noqa: E712
        )
    )
    usuario = result.scalar_one_or_none()
    if not usuario:
        return None

    novo_payload = {"sub": str(usuario.id)}
    return criar_access_token(novo_payload), criar_refresh_token(novo_payload)


async def alterar_senha(
    usuario: Usuario, senha_atual: str, nova_senha: str, db: AsyncSession
) -> bool:
    """Altera senha do usuario. Retorna False se senha atual incorreta."""
    if not verificar_senha(senha_atual, usuario.senha_hash):
        return False

    usuario.senha_hash = hash_senha(nova_senha)
    db.add(usuario)
    return True
