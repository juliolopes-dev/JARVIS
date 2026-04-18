"""
Seed de pessoas de teste para validar a integracao Pessoas <-> Chat.

Uso:
    cd backend && uv run python scripts/seed_pessoas_teste.py

Cria/atualiza pessoas de teste para o unico usuario do sistema.
Idempotente: se a pessoa ja existe (mesmo nome), atualiza relacao/notas.
"""

import asyncio
import sys
from pathlib import Path

# Permite importar app.* quando executado via uv run
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
# Importar todos os modulos .models para o SQLAlchemy resolver relacionamentos
import app.modules.auth.models  # noqa: E402, F401
import app.modules.chat.models  # noqa: E402, F401
import app.modules.checklist.models  # noqa: E402, F401
import app.modules.config.models  # noqa: E402, F401
import app.modules.lembretes.models  # noqa: E402, F401
import app.modules.livros.models  # noqa: E402, F401
import app.modules.notificacoes.models  # noqa: E402, F401
import app.modules.tarefas.models  # noqa: E402, F401
from app.modules.auth.models import Usuario  # noqa: E402
from app.modules.memoria.models import Pessoa  # noqa: E402


PESSOAS_TESTE = [
    {
        "nome": "Rafaela",
        "relacao": "Esposa",
        "notas": "Adora sushi, odeia filmes de terror, faz aniversario em 12 de marco.",
    },
    {
        "nome": "Joao Pedro",
        "relacao": "Filho",
        "notas": "Tem 8 anos, joga futebol aos sabados, gosta de dinossauros.",
    },
    {
        "nome": "Maria Silva",
        "relacao": "Mae",
        "notas": "Mora em Belo Horizonte, ama jardinagem, tem um cachorro chamado Thor.",
    },
    {
        "nome": "Carlos Eduardo",
        "relacao": "Irmao",
        "notas": "Trabalha como arquiteto em Sao Paulo, casou em 2023 com a Beatriz.",
    },
    {
        "nome": "Bruno Santos",
        "relacao": "Amigo",
        "notas": "Amigo de faculdade, trabalha com dados, mora em Curitiba.",
    },
    {
        "nome": "Dra. Helena",
        "relacao": "Medica",
        "notas": "Cardiologista, consultorio na Av. Paulista, ultima consulta foi em marco.",
    },
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Pega o primeiro usuario (Jarvis e single-user)
        result = await db.execute(select(Usuario).limit(1))
        usuario = result.scalar_one_or_none()
        if not usuario:
            print("ERRO: nenhum usuario cadastrado. Crie um usuario antes.")
            return

        print(f"Usuario: {usuario.email} ({usuario.id})")
        print()

        criados = 0
        atualizados = 0

        for dados in PESSOAS_TESTE:
            result = await db.execute(
                select(Pessoa).where(
                    Pessoa.id_usuario == usuario.id,
                    Pessoa.nome == dados["nome"],
                )
            )
            pessoa = result.scalar_one_or_none()

            if pessoa:
                pessoa.relacao = dados["relacao"]
                pessoa.notas = dados["notas"]
                pessoa.flg_ativo = True
                atualizados += 1
                print(f"  [ATUALIZADO] {dados['nome']} ({dados['relacao']})")
            else:
                db.add(Pessoa(
                    id_usuario=usuario.id,
                    nome=dados["nome"],
                    relacao=dados["relacao"],
                    notas=dados["notas"],
                ))
                criados += 1
                print(f"  [CRIADO]     {dados['nome']} ({dados['relacao']})")

        await db.commit()
        print()
        print(f"Total: {criados} criados, {atualizados} atualizados.")


if __name__ == "__main__":
    asyncio.run(main())
