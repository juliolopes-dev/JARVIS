from pydantic import BaseModel


class SubscricaoCreate(BaseModel):
    endpoint: str
    chave_p256dh: str
    chave_auth: str
    dispositivo: str | None = None


class SubscricaoRemover(BaseModel):
    endpoint: str
