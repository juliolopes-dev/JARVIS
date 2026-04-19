"""
Modulo Memoria — gerencia memorias persistentes e pessoas.

Fluxo:
1. Mensagem do usuario → extrair fatos via Mem0
2. Salvar fatos no PostgreSQL com embedding (para busca semantica)
3. Busca semantica via pgvector quando precisar de contexto
"""

import re
import unicodedata
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ia.service import gerar_embedding, get_openai
from app.modules.memoria.models import Memoria, Pessoa
from app.modules.memoria.schemas import PessoaCreate, PessoaUpdate


CATEGORIAS_VALIDAS = {"pessoa", "local", "trabalho", "preferencia", "meta", "fato"}


def _normalizar(texto: str) -> str:
    """Remove acentos e deixa minusculo — Julio costuma digitar sem acento."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.lower()


def _extrair_categoria(conteudo: str) -> tuple[str, str]:
    """
    Se o conteudo vier prefixado com [categoria], separa e retorna (categoria, texto_limpo).
    Senao, retorna ("", conteudo) — cabe ao chamador classificar via LLM.
    """
    match = re.match(r"^\s*\[(\w+)\]\s*(.+)$", conteudo, re.DOTALL)
    if match:
        cat = match.group(1).lower()
        texto = match.group(2).strip()
        if cat in CATEGORIAS_VALIDAS:
            return cat, texto
    return "", conteudo.strip()


async def _classificar_via_llm(conteudo: str) -> str:
    """
    Fallback: pede ao GPT-4o para classificar o fato numa das categorias validas.
    Usado quando o Mem0 nao prefixou com [categoria] (ele as vezes ignora o prompt).
    """
    try:
        cliente = get_openai()
        response = await cliente.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classifique o fato pessoal em UMA palavra, escolhendo entre: "
                        "pessoa, local, trabalho, preferencia, meta, fato. "
                        "pessoa=dados pessoais; local=onde mora/frequenta; trabalho=profissao/cargo/skills; "
                        "preferencia=gostos/hobbies/comidas/filmes favoritos; meta=objetivos/planos/sonhos; "
                        "fato=qualquer outro. Responda SO a palavra, sem pontuacao."
                    ),
                },
                {"role": "user", "content": conteudo},
            ],
            max_tokens=5,
            temperature=0,
        )
        resposta = response.choices[0].message.content.strip().lower().strip(".,[]")
        if resposta in CATEGORIAS_VALIDAS:
            return resposta
    except Exception as e:
        logger.warning("Falha ao classificar memoria: {}", str(e))
    return "fato"


# Instancia global do Mem0 — criar conexao nova a cada mensagem desperdica
# tempo e recursos (reconecta Postgres, recarrega config, recria clientes OpenAI).
# Construida preguicosamente na primeira chamada, reusada em todas seguintes.
_mem0_client = None


def get_mem0():
    """Retorna instancia global do Mem0 (construida sob demanda na primeira chamada)."""
    global _mem0_client
    if _mem0_client is not None:
        return _mem0_client

    from mem0 import Memory

    db_url = settings.database_url
    match = re.match(
        r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url
    )
    db_user, db_pass, db_host, db_port, db_name = match.groups() if match else (
        "postgres", "", "localhost", "5432", "database"
    )

    _mem0_client = Memory.from_config(
        {
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "dbname": db_name,
                    "collection_name": settings.mem0_collection_name,
                    "host": db_host,
                    "port": int(db_port),
                    "user": db_user,
                    "password": db_pass,
                    "embedding_model_dims": 1536,
                },
            },
            "llm": {
                "provider": "openai",
                "config": {"api_key": settings.openai_api_key, "model": "gpt-4o"},
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "api_key": settings.openai_api_key,
                    "model": "text-embedding-3-small",
                },
            },
            "custom_prompt": (
                "Voce e um extrator de fatos pessoais sobre o usuario. "
                "REGRAS OBRIGATORIAS:\n"
                "1. Sempre escreva os fatos em Portugues do Brasil.\n"
                "2. Fatos de LOCALIZACAO: qualquer variacao de 'me mudei', 'agora moro', 'fui para', 'estou em' "
                "significa UPDATE no fato de cidade/localizacao existente — NUNCA crie novo fato de localizacao se ja existe um.\n"
                "3. Fatos de IDADE: qualquer nova idade mencionada e UPDATE do fato de idade existente.\n"
                "4. Fatos de PROFISSAO: novas profissoes ou cargos sao UPDATE do fato de profissao existente.\n"
                "5. Fatos validos: nome, idade, cidade, profissao, preferencias, relacionamentos, habitos, metas, habilidades.\n"
                "6. Ignore informacoes genericas sem relacao pessoal direta com o usuario.\n"
                "7. CLASSIFIQUE cada fato prefixando com a categoria entre colchetes no comeco do texto. "
                "Categorias validas:\n"
                "   [pessoa] — nome, idade, aparencia, dados pessoais do usuario\n"
                "   [local] — onde mora, cidade, bairro, lugares que frequenta\n"
                "   [trabalho] — profissao, cargo, empresa, projetos, habilidades tecnicas\n"
                "   [preferencia] — gostos, odios, hobbies, comidas, filmes, musicas favoritas\n"
                "   [meta] — objetivos, planos, metas de curto/longo prazo, desejos\n"
                "   [fato] — qualquer outro fato pessoal que nao se encaixa acima\n"
                "Exemplo: '[local] Mora em Sao Paulo', '[preferencia] Gosta de sushi', '[trabalho] Trabalha como dev Python'."
            ),
        }
    )
    logger.info("Mem0 inicializado | collection={}", settings.mem0_collection_name)
    return _mem0_client


async def extrair_e_salvar_memoria(
    mensagem: str,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Extrai fatos da mensagem do usuario e salva no banco.
    Chamado apos cada mensagem do usuario para construir memoria persistente.
    """
    try:
        mem0 = get_mem0()

        resultado = mem0.add(
            mensagem,
            user_id=str(id_usuario),
            metadata={"fonte": "chat"},
        )

        logger.info("Mem0 resultado | msg={} | results={}", mensagem[:80], resultado)

        # Espelhar fatos no PostgreSQL (para busca semantica direta via pgvector)
        if resultado and "results" in resultado:
            for item in resultado["results"]:
                evento = item.get("event")
                conteudo_raw = item.get("memory", "")
                id_mem0 = item.get("id", "")
                if not conteudo_raw:
                    continue

                logger.debug("Mem0 retornou | evento={} | raw={}", evento, conteudo_raw)

                # Tenta parsear o prefixo [categoria] inserido pelo custom_prompt.
                # Se o Mem0 ignorou o prompt (acontece), classifica via GPT-4o-mini.
                categoria, conteudo = _extrair_categoria(conteudo_raw)
                if not categoria:
                    categoria = await _classificar_via_llm(conteudo)
                embedding = await gerar_embedding(conteudo)

                if evento == "ADD":
                    memoria = Memoria(
                        id_usuario=id_usuario,
                        id_mem0=id_mem0 or None,
                        conteudo=conteudo,
                        categoria=categoria,
                        embedding=embedding,
                    )
                    db.add(memoria)

                elif evento == "UPDATE" and id_mem0:
                    # Atualizar registro existente pelo id_mem0
                    result = await db.execute(
                        select(Memoria).where(
                            Memoria.id_mem0 == id_mem0,
                            Memoria.id_usuario == id_usuario,
                        )
                    )
                    memoria_existente = result.scalar_one_or_none()
                    if memoria_existente:
                        memoria_existente.conteudo = conteudo
                        memoria_existente.categoria = categoria
                        memoria_existente.embedding = embedding
                        db.add(memoria_existente)
                    else:
                        db.add(Memoria(
                            id_usuario=id_usuario,
                            id_mem0=id_mem0,
                            conteudo=conteudo,
                            categoria=categoria,
                            embedding=embedding,
                        ))

                elif evento == "DELETE" and id_mem0:
                    result = await db.execute(
                        select(Memoria).where(
                            Memoria.id_mem0 == id_mem0,
                            Memoria.id_usuario == id_usuario,
                        )
                    )
                    memoria_existente = result.scalar_one_or_none()
                    if memoria_existente:
                        memoria_existente.flg_ativo = False
                        db.add(memoria_existente)

            await db.flush()

    except Exception as e:
        # Memoria nao pode quebrar o fluxo do chat
        logger.warning("Falha ao extrair memoria: {}", str(e))


async def buscar_memorias_relevantes(
    consulta: str,
    id_usuario: uuid.UUID,
    db: AsyncSession,
    limite: int = 5,
) -> str:
    """
    Busca memorias relevantes via pgvector (cosine similarity) + pessoas mencionadas.
    Retorna string formatada para inserir no system prompt.
    """
    try:
        embedding = await gerar_embedding(consulta)

        # Busca por similaridade usando operador <=> (cosine distance) do pgvector
        from sqlalchemy import text

        result = await db.execute(
            text("""
                SELECT conteudo, 1 - (embedding <=> :embedding) AS similaridade
                FROM memorias
                WHERE id_usuario = :id_usuario AND flg_ativo = true AND embedding IS NOT NULL
                ORDER BY embedding <=> :embedding
                LIMIT :limite
            """),
            {
                "embedding": str(embedding),
                "id_usuario": str(id_usuario),
                "limite": limite,
            },
        )
        memorias = result.fetchall()

        secoes: list[str] = []

        linhas_memoria = [f"- {m[0]}" for m in memorias if m[1] > 0.6]
        if linhas_memoria:
            secoes.append("Fatos relevantes:\n" + "\n".join(linhas_memoria))

        # Detectar pessoas mencionadas na consulta e trazer contexto delas.
        # Match simples por substring case-insensitive no nome — suficiente para
        # um usuario unico com poucas dezenas de pessoas cadastradas.
        pessoas_mencionadas = await _detectar_pessoas_mencionadas(consulta, id_usuario, db)
        if pessoas_mencionadas:
            linhas_pessoas = []
            for p in pessoas_mencionadas:
                detalhe = p.nome
                if p.relacao:
                    detalhe += f" ({p.relacao})"
                if p.notas:
                    detalhe += f" — {p.notas}"
                linhas_pessoas.append(f"- {detalhe}")
            secoes.append("Pessoas mencionadas:\n" + "\n".join(linhas_pessoas))

        return "\n\n".join(secoes)

    except Exception as e:
        logger.warning("Falha ao buscar memorias: {}", str(e))
        return ""


async def _detectar_pessoas_mencionadas(
    consulta: str, id_usuario: uuid.UUID, db: AsyncSession
) -> list[Pessoa]:
    """
    Retorna pessoas cadastradas cujo nome aparece na consulta.
    Comparacao case-insensitive por substring — basta o primeiro nome bater.
    """
    result = await db.execute(
        select(Pessoa).where(
            Pessoa.id_usuario == id_usuario,
            Pessoa.flg_ativo == True,  # noqa: E712
        )
    )
    todas = list(result.scalars())
    if not todas:
        return []

    # Normalizar remove acentos dos dois lados — "irmão" casa com "Irmao", "médica" com "Medica"
    consulta_norm = _normalizar(consulta)
    mencionadas = []
    for pessoa in todas:
        nome_norm = _normalizar(pessoa.nome)
        primeiro_nome = nome_norm.split()[0] if nome_norm else ""
        relacao_norm = _normalizar(pessoa.relacao or "")
        if nome_norm in consulta_norm or (
            primeiro_nome and len(primeiro_nome) >= 3 and primeiro_nome in consulta_norm
        ) or (
            # Match tambem pela relacao — "minha esposa" encontra a pessoa com relacao="Esposa"
            relacao_norm and len(relacao_norm) >= 4 and relacao_norm in consulta_norm
        ):
            mencionadas.append(pessoa)
    return mencionadas


async def listar_memorias(
    id_usuario: uuid.UUID,
    db: AsyncSession,
    categoria: str | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> list[Memoria]:
    """Lista memorias do usuario com filtro opcional por categoria."""
    query = select(Memoria).where(
        Memoria.id_usuario == id_usuario,
        Memoria.flg_ativo == True,  # noqa: E712
    )
    if categoria:
        query = query.where(Memoria.categoria == categoria)

    query = query.order_by(Memoria.criado_em.desc())
    query = query.offset((pagina - 1) * por_pagina).limit(por_pagina)

    result = await db.execute(query)
    return list(result.scalars())


async def desativar_memoria(
    id_memoria: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> bool:
    """Soft delete de memoria. Retorna False se nao encontrada."""
    result = await db.execute(
        select(Memoria).where(
            Memoria.id == id_memoria,
            Memoria.id_usuario == id_usuario,
        )
    )
    memoria = result.scalar_one_or_none()
    if not memoria:
        return False

    memoria.flg_ativo = False
    db.add(memoria)
    return True


# ===== PESSOAS =====

async def criar_pessoa(
    dados: PessoaCreate, id_usuario: uuid.UUID, db: AsyncSession
) -> Pessoa:
    pessoa = Pessoa(id_usuario=id_usuario, **dados.model_dump())
    db.add(pessoa)
    await db.flush()
    return pessoa


async def listar_pessoas(id_usuario: uuid.UUID, db: AsyncSession) -> list[Pessoa]:
    result = await db.execute(
        select(Pessoa).where(
            Pessoa.id_usuario == id_usuario,
            Pessoa.flg_ativo == True,  # noqa: E712
        ).order_by(Pessoa.nome)
    )
    return list(result.scalars())


async def buscar_pessoa(
    id_pessoa: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> Pessoa | None:
    result = await db.execute(
        select(Pessoa).where(
            Pessoa.id == id_pessoa,
            Pessoa.id_usuario == id_usuario,
        )
    )
    return result.scalar_one_or_none()


async def atualizar_pessoa(
    id_pessoa: uuid.UUID,
    dados: PessoaUpdate,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> Pessoa | None:
    pessoa = await buscar_pessoa(id_pessoa, id_usuario, db)
    if not pessoa:
        return None

    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(pessoa, campo, valor)

    db.add(pessoa)
    return pessoa


async def desativar_pessoa(
    id_pessoa: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> bool:
    pessoa = await buscar_pessoa(id_pessoa, id_usuario, db)
    if not pessoa:
        return False
    pessoa.flg_ativo = False
    db.add(pessoa)
    return True
