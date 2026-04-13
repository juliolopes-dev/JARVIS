import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.core.scheduler import scheduler
from app.middleware.cors import configurar_cors
from app.middleware.rate_limit import configurar_rate_limit
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.lembretes.router import router as lembretes_router
from app.modules.memoria.router import router as memoria_router
from app.modules.notificacoes.router import router as notificacoes_router


# ─── Loguru ──────────────────────────────────────────────────────────────────

def _filtrar_dados_sensiveis(record: dict) -> bool:
    """Bloqueia logs que contenham dados sensiveis."""
    mensagem = record["message"].lower()
    palavras_sensiveis = ("password", "senha", "token", "secret", "authorization", "api_key")
    return not any(p in mensagem for p in palavras_sensiveis)


def _configurar_loguru() -> None:
    logger.remove()  # Remove handler padrao

    if settings.environment == "production":
        # JSON em producao
        logger.add(
            sys.stdout,
            format="{time} {level} {message}",
            serialize=True,
            filter=_filtrar_dados_sensiveis,
            level="INFO",
        )
    else:
        # Colorido em desenvolvimento
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
            filter=_filtrar_dados_sensiveis,
            level="DEBUG",
        )


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _configurar_loguru()
    logger.info("Jarvis iniciando... ambiente={}", settings.environment)
    scheduler.start()
    logger.info("APScheduler iniciado")
    yield
    scheduler.shutdown()
    logger.info("Jarvis encerrando...")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Jarvis",
    description="Assistente pessoal de IA",
    version="0.1.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Middlewares
configurar_cors(app)
configurar_rate_limit(app)


# ─── Exception handler global ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def handler_erro_global(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Erro nao tratado | path={} | erro={}", request.url.path, str(exc))
    mensagem = str(exc) if settings.environment != "production" else "Erro interno do servidor"
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": mensagem},
    )


# ─── Rotas da API ─────────────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(memoria_router, prefix="/api/memoria", tags=["memoria"])
app.include_router(lembretes_router, prefix="/api/lembretes", tags=["lembretes"])
app.include_router(notificacoes_router, prefix="/api/notificacoes", tags=["notificacoes"])


@app.get("/api/health", tags=["sistema"])
async def health():
    """Healthcheck — usado pelo EasyPanel para verificar saude do servico."""
    return {"status": "ok", "service": "jarvis"}


@app.get("/api/version", tags=["sistema"])
async def version():
    """Versao atual do backend — usado pelo frontend para cache busting."""
    version_file = Path(__file__).parent.parent.parent / "public" / "version.json"
    if version_file.exists():
        import json
        return json.loads(version_file.read_text())
    return {"version": "0.1.0"}


# ─── Frontend estático (producao) ─────────────────────────────────────────────

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.responses import FileResponse
    from fastapi import Response
    import mimetypes

    # Serve os assets do React
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # Arquivos estaticos da raiz que NAO devem ser capturados pelo SPA catch-all
    _static_root_files = {
        "sw.js", "sw.mjs", "registerSW.js", "manifest.webmanifest",
        "favicon.svg", "favicon.ico", "robots.txt",
    }

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Servir arquivos estaticos da raiz diretamente
        if full_path in _static_root_files:
            arquivo = frontend_dist / full_path
            if arquivo.exists():
                media_type, _ = mimetypes.guess_type(full_path)
                return FileResponse(str(arquivo), media_type=media_type or "application/octet-stream")
        # SPA fallback — todas as outras rotas retornam index.html
        index = frontend_dist / "index.html"
        return FileResponse(str(index))
