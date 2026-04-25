"""
Modulo Memoria — gerencia memorias persistentes e pessoas.

Fluxo:
1. Mensagem do usuario → extrair fatos via Mem0
2. Salvar fatos no PostgreSQL com embedding (para busca semantica)
3. Busca semantica via pgvector quando precisar de contexto
"""

import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ia.service import gerar_embedding, get_openai
from app.modules.memoria.models import Evento, Memoria, Pessoa
from app.modules.memoria.schemas import EventoCreate, EventoUpdate, PessoaCreate, PessoaUpdate


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


def _score_combinado(similaridade: float, data_referencia: datetime, decay_dias: int = 365) -> float:
    """Score = 70% similaridade semântica + 30% recência (decay linear)."""
    agora = datetime.now(timezone.utc)
    ref = data_referencia if data_referencia.tzinfo else data_referencia.replace(tzinfo=timezone.utc)
    dias = max(0, (agora - ref).days)
    recencia = max(0.0, 1.0 - dias / decay_dias)
    return similaridade * 0.7 + recencia * 0.3


async def buscar_memorias_relevantes(
    consulta: str,
    id_usuario: uuid.UUID,
    db: AsyncSession,
    limite: int = 5,
) -> str:
    """
    Busca fatos + eventos relevantes via pgvector com score combinado (similaridade + recência).
    Retorna string formatada para inserir no system prompt.
    """
    try:
        embedding = await gerar_embedding(consulta)

        from sqlalchemy import text

        # ── Fatos (memorias) ──────────────────────────────────────────────────
        result = await db.execute(
            text("""
                SELECT conteudo, 1 - (embedding <=> :embedding) AS similaridade, criado_em
                FROM memorias
                WHERE id_usuario = :id_usuario AND flg_ativo = true AND embedding IS NOT NULL
                ORDER BY embedding <=> :embedding
                LIMIT :limite
            """),
            {"embedding": str(embedding), "id_usuario": str(id_usuario), "limite": limite},
        )
        fatos_raw = result.fetchall()

        fatos_scored = []
        for conteudo, sim, criado_em in fatos_raw:
            if sim < 0.45:
                continue
            score = _score_combinado(sim, criado_em, decay_dias=365)
            fatos_scored.append((conteudo, score))

        fatos_scored.sort(key=lambda x: x[1], reverse=True)

        # ── Eventos (memoria episodica) ───────────────────────────────────────
        result_evt = await db.execute(
            text("""
                SELECT resumo, categoria, dat_ocorreu,
                       1 - (embedding <=> :embedding) AS similaridade
                FROM eventos
                WHERE id_usuario = :id_usuario AND flg_ativo = true AND embedding IS NOT NULL
                ORDER BY embedding <=> :embedding
                LIMIT 10
            """),
            {"embedding": str(embedding), "id_usuario": str(id_usuario)},
        )
        eventos_raw = result_evt.fetchall()

        brt = ZoneInfo("America/Sao_Paulo")
        eventos_scored = []
        for resumo, categoria, dat_ocorreu, sim in eventos_raw:
            if sim < 0.40:
                continue
            # Eventos decaem mais rapido (180 dias) — contexto recente importa mais
            score = _score_combinado(sim, dat_ocorreu, decay_dias=180)
            eventos_scored.append((resumo, categoria, dat_ocorreu, score))

        eventos_scored.sort(key=lambda x: x[3], reverse=True)

        # ── Montar secoes do contexto ─────────────────────────────────────────
        secoes: list[str] = []

        linhas_memoria = [f"- {f[0]}" for f in fatos_scored]
        if linhas_memoria:
            secoes.append("Fatos relevantes:\n" + "\n".join(linhas_memoria))

        if eventos_scored:
            linhas_eventos = []
            for resumo, categoria, dat_ocorreu, _ in eventos_scored[:5]:
                dat_fmt = dat_ocorreu.astimezone(brt).strftime("%d/%m/%Y")
                linhas_eventos.append(f"- [{dat_fmt}] {resumo} ({categoria})")
            secoes.append("Eventos recentes relevantes:\n" + "\n".join(linhas_eventos))

        # Detectar pessoas mencionadas por nome/relacao (substring normalizado)
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


# ===== CONSOLIDACAO =====

async def consolidar_memorias_usuario(id_usuario: uuid.UUID) -> int:
    """
    Busca pares de fatos com similaridade > 0.85 e pede ao GPT-4o mini para decidir
    se devem ser mesclados. Retorna quantas memorias foram consolidadas.
    Roda em sessao propria — nao depende de db externo.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                text("""
                    SELECT a.id, a.conteudo, b.id AS id_b, b.conteudo AS conteudo_b,
                           1 - (a.embedding <=> b.embedding) AS similaridade
                    FROM memorias a
                    JOIN memorias b ON a.id_usuario = b.id_usuario
                    WHERE a.id_usuario = :id_usuario
                      AND a.id < b.id
                      AND a.flg_ativo = true
                      AND b.flg_ativo = true
                      AND a.embedding IS NOT NULL
                      AND b.embedding IS NOT NULL
                      AND 1 - (a.embedding <=> b.embedding) > 0.85
                    ORDER BY similaridade DESC
                    LIMIT 20
                """),
                {"id_usuario": str(id_usuario)},
            )
            pares = result.fetchall()

            if not pares:
                return 0

            cliente = get_openai()
            consolidados = 0

            for id_a, conteudo_a, id_b, conteudo_b, _ in pares:
                try:
                    resp = await cliente.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Analise dois fatos de memoria pessoal. "
                                    "Se forem duplicados ou contraditorios, responda com JSON: "
                                    '{"consolidar": true, "fato_final": "texto unificado em portugues"} '
                                    "Se forem complementares ou distintos, responda apenas: "
                                    '{"consolidar": false}'
                                ),
                            },
                            {"role": "user", "content": f"Fato A: {conteudo_a}\nFato B: {conteudo_b}"},
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=100,
                        temperature=0,
                    )
                    dados = json.loads(resp.choices[0].message.content)

                    if not dados.get("consolidar") or not dados.get("fato_final"):
                        continue

                    fato_final = dados["fato_final"]
                    novo_embedding = await gerar_embedding(fato_final)

                    mem_a = (await db.execute(select(Memoria).where(Memoria.id == id_a))).scalar_one_or_none()
                    mem_b = (await db.execute(select(Memoria).where(Memoria.id == id_b))).scalar_one_or_none()

                    if mem_a:
                        mem_a.conteudo = fato_final
                        mem_a.embedding = novo_embedding
                        db.add(mem_a)
                    if mem_b:
                        mem_b.flg_ativo = False
                        db.add(mem_b)

                    consolidados += 1
                    logger.debug("Memorias consolidadas | a={} | b={} | resultado={}", id_a, id_b, fato_final)

                except Exception as e:
                    logger.warning("Falha ao consolidar par ({}, {}): {}", id_a, id_b, str(e))

            await db.commit()
            logger.info("Consolidacao | id_usuario={} | consolidados={}", id_usuario, consolidados)
            return consolidados

        except Exception as e:
            await db.rollback()
            logger.warning("Falha na consolidacao de memorias: {}", str(e))
            return 0


async def _job_consolidar_memorias() -> None:
    """Job APScheduler — roda toda segunda-feira as 03:00 BRT."""
    from app.core.database import AsyncSessionLocal
    from app.modules.auth.models import Usuario

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Usuario.id).where(Usuario.flg_ativo == True))  # noqa: E712
        ids = result.scalars().all()

    total = 0
    for id_usuario in ids:
        consolidados = await consolidar_memorias_usuario(id_usuario)
        total += consolidados

    logger.info("Job consolidacao concluido | total={}", total)


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


# ===== EVENTOS (memoria episodica) =====

async def criar_evento(
    dados: EventoCreate, id_usuario: uuid.UUID, db: AsyncSession
) -> Evento:
    """Cria evento e gera embedding do resumo para busca semantica."""
    evento = Evento(id_usuario=id_usuario, **dados.model_dump())
    try:
        evento.embedding = await gerar_embedding(dados.resumo)
    except Exception as e:
        logger.warning(f"Falha ao gerar embedding do evento: {e}")
    db.add(evento)
    await db.flush()
    return evento


async def listar_eventos(
    id_usuario: uuid.UUID,
    db: AsyncSession,
    categoria: str | None = None,
    loja: str | None = None,
    id_pessoa: uuid.UUID | None = None,
    dat_inicio: datetime | None = None,
    dat_fim: datetime | None = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> list[Evento]:
    query = select(Evento).where(
        Evento.id_usuario == id_usuario,
        Evento.flg_ativo == True,  # noqa: E712
    )
    if categoria:
        query = query.where(Evento.categoria == categoria)
    if loja:
        query = query.where(Evento.lojas.any(loja))
    if id_pessoa:
        query = query.where(Evento.pessoas_envolvidas.any(id_pessoa))
    if dat_inicio:
        query = query.where(Evento.dat_ocorreu >= dat_inicio)
    if dat_fim:
        query = query.where(Evento.dat_ocorreu <= dat_fim)

    offset = (pagina - 1) * por_pagina
    query = query.order_by(Evento.dat_ocorreu.desc()).offset(offset).limit(por_pagina)

    result = await db.execute(query)
    return list(result.scalars())


async def buscar_evento(
    id_evento: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> Evento | None:
    result = await db.execute(
        select(Evento).where(
            Evento.id == id_evento,
            Evento.id_usuario == id_usuario,
        )
    )
    return result.scalar_one_or_none()


async def atualizar_evento(
    id_evento: uuid.UUID,
    dados: EventoUpdate,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> Evento | None:
    evento = await buscar_evento(id_evento, id_usuario, db)
    if not evento:
        return None

    campos = dados.model_dump(exclude_none=True)
    for campo, valor in campos.items():
        setattr(evento, campo, valor)

    if "resumo" in campos:
        try:
            evento.embedding = await gerar_embedding(evento.resumo)
        except Exception as e:
            logger.warning(f"Falha ao regenerar embedding do evento: {e}")

    db.add(evento)
    return evento


async def desativar_evento(
    id_evento: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> bool:
    evento = await buscar_evento(id_evento, id_usuario, db)
    if not evento:
        return False
    evento.flg_ativo = False
    db.add(evento)
    return True
