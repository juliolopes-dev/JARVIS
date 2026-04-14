import re
import uuid
from datetime import datetime, timezone
from io import BytesIO

import pdfplumber
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.livros.models import Livro, LivroChunk, LeituraProgresso
from app.modules.livros.schemas import ProgressoUpdate


# ─── Helpers ──────────────────────────────────────────────────────────────────

_PADRAO_CAPITULO = re.compile(
    r'^(cap[ií]tulo\s+\w+|chapter\s+\w+|parte\s+\w+|[IVXLC]+\.|[0-9]+\.?\s+[A-Z])',
    re.IGNORECASE,
)


def _detectar_capitulo(texto: str) -> str | None:
    """Retorna o titulo do capitulo se a linha parece ser um cabecalho."""
    linha = texto.strip().split('\n')[0].strip()
    if len(linha) < 3 or len(linha) > 120:
        return None
    if _PADRAO_CAPITULO.match(linha):
        return linha
    # Linha toda em maiusculo com tamanho razoavel = provavel cabecalho
    if linha.isupper() and 3 < len(linha) < 80:
        return linha
    return None


def _extrair_texto_pdf(conteudo_bytes: bytes) -> tuple[str, int]:
    """Extrai texto de um PDF e retorna (texto_completo, total_paginas)."""
    with pdfplumber.open(BytesIO(conteudo_bytes)) as pdf:
        total_paginas = len(pdf.pages)
        partes: list[str] = []
        for page in pdf.pages:
            texto = page.extract_text()
            if texto:
                partes.append(texto)
    return '\n\n'.join(partes), total_paginas


def _dividir_em_chunks(texto: str, palavras_por_chunk: int) -> list[dict]:
    """
    Divide o texto em chunks respeitando paragrafos.
    Retorna lista de dicts com {conteudo, capitulo, total_palavras}.
    """
    paragrafos = [p.strip() for p in texto.split('\n\n') if p.strip()]

    chunks: list[dict] = []
    chunk_atual: list[str] = []
    palavras_atual = 0
    capitulo_atual: str | None = None

    for paragrafo in paragrafos:
        # Detectar mudanca de capitulo
        cap = _detectar_capitulo(paragrafo)
        if cap:
            capitulo_atual = cap

        palavras_paragrafo = len(paragrafo.split())

        # Se adicionar este paragrafo exceder o limite, fechar chunk atual
        if chunk_atual and palavras_atual + palavras_paragrafo > palavras_por_chunk * 1.4:
            chunks.append({
                'conteudo': '\n\n'.join(chunk_atual),
                'capitulo': capitulo_atual,
                'total_palavras': palavras_atual,
            })
            chunk_atual = []
            palavras_atual = 0

        chunk_atual.append(paragrafo)
        palavras_atual += palavras_paragrafo

        # Chunk cheio — fechar
        if palavras_atual >= palavras_por_chunk:
            chunks.append({
                'conteudo': '\n\n'.join(chunk_atual),
                'capitulo': capitulo_atual,
                'total_palavras': palavras_atual,
            })
            chunk_atual = []
            palavras_atual = 0

    # Sobra
    if chunk_atual:
        chunks.append({
            'conteudo': '\n\n'.join(chunk_atual),
            'capitulo': capitulo_atual,
            'total_palavras': palavras_atual,
        })

    return chunks


# ─── CRUD Livros ──────────────────────────────────────────────────────────────

async def processar_upload(
    id_usuario: uuid.UUID,
    titulo: str,
    autor: str | None,
    conteudo_bytes: bytes,
    palavras_por_chunk: int,
    db: AsyncSession,
) -> Livro:
    """Extrai texto do PDF, divide em chunks e salva tudo no banco."""
    logger.info("Processando PDF | titulo={} | tamanho={}b", titulo, len(conteudo_bytes))

    texto, total_paginas = _extrair_texto_pdf(conteudo_bytes)
    if not texto.strip():
        raise ValueError("Nao foi possivel extrair texto do PDF. O arquivo pode ser escaneado/imagem.")

    raw_chunks = _dividir_em_chunks(texto, palavras_por_chunk)
    logger.info("PDF processado | paginas={} | chunks={}", total_paginas, len(raw_chunks))

    livro = Livro(
        id_usuario=id_usuario,
        titulo=titulo,
        autor=autor,
        total_paginas=total_paginas,
        total_chunks=len(raw_chunks),
    )
    db.add(livro)
    await db.flush()  # gera o id do livro

    for i, c in enumerate(raw_chunks, start=1):
        db.add(LivroChunk(
            id_livro=livro.id,
            numero=i,
            capitulo=c['capitulo'],
            conteudo=c['conteudo'],
            total_palavras=c['total_palavras'],
        ))

    # Criar progresso inicial
    db.add(LeituraProgresso(
        id_livro=livro.id,
        chunk_atual=1,
        tamanho_chunk=palavras_por_chunk,
    ))

    await db.commit()

    # Recarregar com o relacionamento progresso (refresh nao carrega lazy relationships no async)
    result = await db.execute(
        select(Livro)
        .where(Livro.id == livro.id)
        .options(selectinload(Livro.progresso))
    )
    return result.scalar_one()


async def listar_livros(id_usuario: uuid.UUID, db: AsyncSession) -> list[Livro]:
    result = await db.execute(
        select(Livro)
        .where(Livro.id_usuario == id_usuario, Livro.flg_ativo == True)  # noqa: E712
        .options(selectinload(Livro.progresso))
        .order_by(Livro.dat_upload.desc())
    )
    return list(result.scalars().all())


async def obter_livro(id_livro: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession) -> Livro | None:
    result = await db.execute(
        select(Livro)
        .where(Livro.id == id_livro, Livro.id_usuario == id_usuario, Livro.flg_ativo == True)  # noqa: E712
        .options(selectinload(Livro.progresso))
    )
    return result.scalar_one_or_none()


async def deletar_livro(id_livro: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession) -> bool:
    livro = await obter_livro(id_livro, id_usuario, db)
    if not livro:
        return False
    livro.flg_ativo = False
    await db.commit()
    return True


# ─── Leitura ──────────────────────────────────────────────────────────────────

async def _obter_chunk(id_livro: uuid.UUID, numero: int, db: AsyncSession) -> LivroChunk | None:
    result = await db.execute(
        select(LivroChunk).where(
            LivroChunk.id_livro == id_livro,
            LivroChunk.numero == numero,
        )
    )
    return result.scalar_one_or_none()


async def _obter_progresso(id_livro: uuid.UUID, db: AsyncSession) -> LeituraProgresso | None:
    result = await db.execute(
        select(LeituraProgresso).where(LeituraProgresso.id_livro == id_livro)
    )
    return result.scalar_one_or_none()


def _fim_de_capitulo(chunk: LivroChunk, proximo: LivroChunk | None) -> bool:
    """Verdadeiro se o chunk atual e o ultimo do seu capitulo."""
    if proximo is None:
        return True
    # Mudou de capitulo
    if proximo.capitulo and proximo.capitulo != chunk.capitulo:
        return True
    return False


async def ler_proximo(
    id_livro: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> dict | None:
    """
    Retorna o chunk atual e avanca o ponteiro.
    Retorna None se livro nao encontrado.
    """
    livro = await obter_livro(id_livro, id_usuario, db)
    if not livro:
        return None

    progresso = await _obter_progresso(id_livro, db)
    if not progresso or progresso.flg_concluido:
        return None

    chunk = await _obter_chunk(id_livro, progresso.chunk_atual, db)
    if not chunk:
        return None

    proximo_chunk = await _obter_chunk(id_livro, progresso.chunk_atual + 1, db)
    fim_capitulo = _fim_de_capitulo(chunk, proximo_chunk)
    livro_concluido = proximo_chunk is None

    # Gerar resumo + perguntas ao fim do capitulo (modo estudo ou nao)
    resumo: str | None = None
    perguntas: list[str] | None = None

    if fim_capitulo:
        resumo, perguntas = await _gerar_resumo_e_perguntas(
            livro.titulo, chunk.capitulo, chunk.conteudo, progresso.flg_modo_estudo
        )

    # Salvar no Mem0 se concluiu o livro
    if livro_concluido:
        await _salvar_memoria_livro(id_usuario, livro.titulo, livro.autor)

    # Atualizar progresso
    if livro_concluido:
        progresso.flg_concluido = True
        progresso.dat_conclusao = datetime.now(timezone.utc)
    else:
        progresso.chunk_atual += 1

    progresso.dat_ultimo_acesso = datetime.now(timezone.utc)
    await db.commit()

    porcentagem = round((chunk.numero / livro.total_chunks) * 100, 1)

    return {
        'livro_id': livro.id,
        'titulo_livro': livro.titulo,
        'chunk': chunk,
        'chunk_atual': chunk.numero,
        'total_chunks': livro.total_chunks,
        'porcentagem': porcentagem,
        'capitulo_concluido': fim_capitulo,
        'livro_concluido': livro_concluido,
        'resumo_capitulo': resumo,
        'perguntas_estudo': perguntas,
    }


async def ler_anterior(
    id_livro: uuid.UUID,
    id_usuario: uuid.UUID,
    db: AsyncSession,
) -> dict | None:
    """Volta um chunk sem alterar progresso."""
    livro = await obter_livro(id_livro, id_usuario, db)
    if not livro:
        return None

    progresso = await _obter_progresso(id_livro, db)
    if not progresso:
        return None

    numero_anterior = max(1, progresso.chunk_atual - 1)
    chunk = await _obter_chunk(id_livro, numero_anterior, db)
    if not chunk:
        return None

    # Volta o ponteiro
    progresso.chunk_atual = numero_anterior
    progresso.flg_concluido = False
    progresso.dat_conclusao = None
    await db.commit()

    porcentagem = round((chunk.numero / livro.total_chunks) * 100, 1)

    return {
        'livro_id': livro.id,
        'titulo_livro': livro.titulo,
        'chunk': chunk,
        'chunk_atual': chunk.numero,
        'total_chunks': livro.total_chunks,
        'porcentagem': porcentagem,
        'capitulo_concluido': False,
        'livro_concluido': False,
        'resumo_capitulo': None,
        'perguntas_estudo': None,
    }


async def atualizar_progresso(
    id_livro: uuid.UUID,
    id_usuario: uuid.UUID,
    dados: ProgressoUpdate,
    db: AsyncSession,
) -> LeituraProgresso | None:
    livro = await obter_livro(id_livro, id_usuario, db)
    if not livro:
        return None

    progresso = await _obter_progresso(id_livro, db)
    if not progresso:
        return None

    if dados.tamanho_chunk is not None:
        progresso.tamanho_chunk = dados.tamanho_chunk
    if dados.flg_modo_estudo is not None:
        progresso.flg_modo_estudo = dados.flg_modo_estudo

    await db.commit()
    await db.refresh(progresso)
    return progresso


# ─── IA: resumo e perguntas ───────────────────────────────────────────────────

async def _gerar_resumo_e_perguntas(
    titulo_livro: str,
    capitulo: str | None,
    conteudo: str,
    modo_estudo: bool,
) -> tuple[str | None, list[str] | None]:
    """Gera resumo do capitulo e, se modo estudo, perguntas de fixacao."""
    try:
        from app.modules.ia.service import get_openai

        cliente = get_openai()
        ref = f'capítulo "{capitulo}"' if capitulo else 'trecho'

        response = await cliente.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": (
                    f'Você está lendo o livro "{titulo_livro}". '
                    f'Faça um resumo conciso do {ref} abaixo em 3-5 frases, '
                    f'destacando os pontos principais:\n\n{conteudo[:3000]}'
                ),
            }],
            max_tokens=300,
            temperature=0.5,
        )
        resumo = response.choices[0].message.content.strip()

        perguntas: list[str] | None = None
        if modo_estudo:
            resp = await cliente.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": (
                        f'Com base no {ref} do livro "{titulo_livro}", '
                        f'crie exatamente 3 perguntas de fixação curtas e objetivas. '
                        f'Retorne apenas as perguntas numeradas (1. 2. 3.), sem introdução:\n\n{conteudo[:3000]}'
                    ),
                }],
                max_tokens=200,
                temperature=0.5,
            )
            texto_perguntas = resp.choices[0].message.content.strip()
            perguntas = [
                linha.strip()
                for linha in texto_perguntas.split('\n')
                if linha.strip() and linha[0].isdigit()
            ][:3]

        return resumo, perguntas

    except Exception as e:
        logger.warning("Falha ao gerar resumo/perguntas: {}", str(e))
        return None, None


async def _salvar_memoria_livro(
    id_usuario: uuid.UUID,
    titulo: str,
    autor: str | None,
) -> None:
    """Salva no Mem0 que o usuario concluiu o livro."""
    try:
        from datetime import date
        from app.modules.memoria.service import extrair_e_salvar_memoria
        from app.core.database import AsyncSessionLocal

        texto = f'Julio concluiu a leitura do livro "{titulo}"'
        if autor:
            texto += f' de {autor}'
        texto += f' em {date.today().strftime("%d/%m/%Y")}.'

        async with AsyncSessionLocal() as db:
            await extrair_e_salvar_memoria(texto, id_usuario, db)

        logger.info("Memoria de leitura salva | livro={}", titulo)
    except Exception as e:
        logger.warning("Falha ao salvar memoria de leitura: {}", str(e))
