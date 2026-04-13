from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Limiter global — usado via decorador nas rotas
limiter = Limiter(key_func=get_remote_address)


def configurar_rate_limit(app: FastAPI) -> None:
    """Registra o limiter e handler de erro no app FastAPI."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
