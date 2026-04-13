import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class RegistrarRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    tipo: str = "bearer"


class UsuarioResponse(BaseModel):
    id: uuid.UUID
    cod_usuario: int
    nome: str
    email: str
    flg_ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str
