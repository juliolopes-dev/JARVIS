import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Importar Base e todos os modelos para autogenerate funcionar
from app.core.config import settings
from app.core.database import Base

# Importar todos os modelos (obrigatorio para autogenerate detectar as tabelas)
from app.modules.auth.models import Usuario  # noqa: F401
from app.modules.chat.models import Conversa, Mensagem  # noqa: F401
from app.modules.config.models import Configuracao  # noqa: F401
from app.modules.lembretes.models import Lembrete  # noqa: F401
from app.modules.memoria.models import Memoria, Pessoa  # noqa: F401
from app.modules.notificacoes.models import SubscricaoPush  # noqa: F401
from app.modules.tarefas.models import TarefaAgendada  # noqa: F401

# Config do Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline — gera SQL sem conectar ao banco."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Modo online — conecta ao banco e aplica migrations."""
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
