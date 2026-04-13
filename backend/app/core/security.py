from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica senha contra o hash armazenado."""
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_access_token(dados: dict) -> str:
    """Cria JWT de acesso com expiracao configurada."""
    payload = dados.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expires_minutes
    )
    payload.update({"exp": expiracao, "tipo": "access"})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def criar_refresh_token(dados: dict) -> str:
    """Cria JWT de refresh com expiracao longa."""
    payload = dados.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expires_days
    )
    payload.update({"exp": expiracao, "tipo": "refresh"})
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict | None:
    """Decodifica e valida JWT. Retorna None se invalido."""
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
