"""
APScheduler configurado com SQLAlchemyJobStore.
Jobs persistidos no PostgreSQL — nao perdem em restart do container.
"""

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

# Converter URL asyncpg -> psycopg2 (APScheduler usa driver sincrono)
def _url_sincrona() -> str:
    url = settings.database_url
    if "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


scheduler = AsyncIOScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=_url_sincrona()),
    },
    executors={
        "default": AsyncIOExecutor(),
    },
    job_defaults={
        "coalesce": True,       # Se atrasou multiplos disparos, executa uma vez
        "max_instances": 1,
        "misfire_grace_time": 300,  # 5 minutos de tolerancia
    },
    timezone="America/Sao_Paulo",
)
