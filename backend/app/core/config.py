from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Banco
    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        """Normaliza qualquer formato de URL PostgreSQL para postgresql+asyncpg://
        Remove parametros incompativeis com asyncpg (sslmode, etc).
        """
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Remover parametros de query incompativeis com asyncpg
        if "?" in v:
            base, params = v.split("?", 1)
            # Filtrar apenas parametros suportados pelo asyncpg
            params_suportados = []
            for param in params.split("&"):
                chave = param.split("=")[0].lower()
                if chave not in ("sslmode", "ssl", "connect_timeout", "application_name"):
                    params_suportados.append(param)
            v = base + ("?" + "&".join(params_suportados) if params_suportados else "")
        return v

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 600
    jwt_refresh_expires_days: int = 30

    # Servidor
    port: int = 8000
    environment: str = "development"

    # CORS
    frontend_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Logs
    log_level: str = "info"

    # APIs de IA
    anthropic_api_key: str
    openai_api_key: str
    openai_admin_key: str = ""  # Usada apenas para consultar /v1/organization/usage/*

    # Mem0
    mem0_collection_name: str = "jarvis_memories"

    # ElevenLabs (Fase 5)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # Web Push (Fase 3)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claims_email: str = ""

    # WhatsApp via Evolution API (Modo 1 — Observador)
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance_name: str = ""
    evolution_webhook_secret: str = ""
    whatsapp_enabled: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
