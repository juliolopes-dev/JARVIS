import uuid
from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import buscar_contexto, salvar_contexto
from app.modules.chat.models import Conversa, Mensagem
from app.modules.ia import service as ia_service
from app.modules.memoria import service as memoria_service


async def criar_conversa(
    id_usuario: uuid.UUID, titulo: str | None, db: AsyncSession
) -> Conversa:
    conversa = Conversa(id_usuario=id_usuario, titulo=titulo)
    db.add(conversa)
    await db.flush()
    return conversa


async def listar_conversas(
    id_usuario: uuid.UUID,
    db: AsyncSession,
    pagina: int = 1,
    por_pagina: int = 20,
) -> list[Conversa]:
    result = await db.execute(
        select(Conversa)
        .where(Conversa.id_usuario == id_usuario, Conversa.flg_ativa == True)  # noqa: E712
        .order_by(Conversa.atualizado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    )
    return list(result.scalars())


async def buscar_conversa(
    id_conversa: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> Conversa | None:
    result = await db.execute(
        select(Conversa).where(
            Conversa.id == id_conversa,
            Conversa.id_usuario == id_usuario,
        )
    )
    return result.scalar_one_or_none()


async def arquivar_conversa(
    id_conversa: uuid.UUID, id_usuario: uuid.UUID, db: AsyncSession
) -> bool:
    conversa = await buscar_conversa(id_conversa, id_usuario, db)
    if not conversa:
        return False
    conversa.flg_ativa = False
    db.add(conversa)
    return True


async def listar_mensagens(
    id_conversa: uuid.UUID,
    db: AsyncSession,
    pagina: int = 1,
    por_pagina: int = 50,
) -> list[Mensagem]:
    result = await db.execute(
        select(Mensagem)
        .where(Mensagem.id_conversa == id_conversa)
        .order_by(Mensagem.criado_em.asc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    )
    return list(result.scalars())


async def enviar_mensagem_stream(
    id_conversa: uuid.UUID,
    id_usuario: uuid.UUID,
    conteudo: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Processa mensagem do usuario e faz streaming da resposta do Jarvis.
    Yields: chunks no formato SSE (data: ...\n\n)
    """
    # 1. Salvar mensagem do usuario
    msg_usuario = Mensagem(
        id_conversa=id_conversa,
        papel="user",
        conteudo=conteudo,
    )
    db.add(msg_usuario)
    await db.flush()

    # 2. Extrair memoria em background com sessao propria (nao bloqueia o streaming)
    import asyncio
    from app.core.database import AsyncSessionLocal

    async def _extrair_memoria_background():
        async with AsyncSessionLocal() as sessao_memoria:
            try:
                await memoria_service.extrair_e_salvar_memoria(conteudo, id_usuario, sessao_memoria)
                await sessao_memoria.commit()
            except Exception as e:
                await sessao_memoria.rollback()
                logger.warning("Falha na extracao de memoria (background): {}", str(e))

    asyncio.create_task(_extrair_memoria_background())

    # 3. Buscar contexto do Redis + historico recente
    contexto_redis = await buscar_contexto(str(id_conversa))
    if not contexto_redis:
        # Buscar ultimas 50 mensagens do banco (cold start)
        msgs_historico = await listar_mensagens(id_conversa, db, por_pagina=50)
        contexto_redis = [
            {"role": m.papel, "content": m.conteudo} for m in msgs_historico[:-1]  # Excluir a atual
        ]

    # 4. Buscar memorias relevantes (20 fatos por similaridade semantica)
    contexto_memoria = await memoria_service.buscar_memorias_relevantes(
        conteudo, id_usuario, db, limite=20
    )

    # 5. Montar mensagens para a IA
    mensagens_ia = contexto_redis + [{"role": "user", "content": conteudo}]

    # 6. Streaming da resposta
    resposta_completa = ""
    modelo_usado = ""
    tokens_entrada = 0
    tokens_saida = 0

    async def _gerar():
        nonlocal resposta_completa, modelo_usado, tokens_entrada, tokens_saida

        async for chunk, modelo, t_entrada, t_saida in ia_service.gerar_resposta_stream(
            mensagens_ia, contexto_memoria
        ):
            if chunk:
                resposta_completa += chunk
                modelo_usado = modelo
                yield f"data: {chunk}\n\n"
            elif t_entrada > 0 or t_saida > 0:
                tokens_entrada = t_entrada
                tokens_saida = t_saida

        yield "data: [DONE]\n\n"

    async for evento in _gerar():
        yield evento

    # 7. Salvar resposta do assistente no banco
    msg_assistente = Mensagem(
        id_conversa=id_conversa,
        papel="assistant",
        conteudo=resposta_completa,
        modelo_usado=modelo_usado,
        tokens_entrada=tokens_entrada,
        tokens_saida=tokens_saida,
    )
    db.add(msg_assistente)

    # 8. Atualizar contexto no Redis (ultimas 50 mensagens)
    novo_contexto = contexto_redis + [
        {"role": "user", "content": conteudo},
        {"role": "assistant", "content": resposta_completa},
    ]
    await salvar_contexto(str(id_conversa), novo_contexto[-50:])

    # 9. Gerar titulo se for a primeira mensagem da conversa
    conversa = await buscar_conversa(id_conversa, id_usuario, db)
    if conversa and not conversa.titulo:
        try:
            titulo = await ia_service.gerar_titulo(conteudo)
            conversa.titulo = titulo
            db.add(conversa)
        except Exception as e:
            logger.warning("Falha ao gerar titulo: {}", str(e))

    await db.commit()
    logger.info(
        "Mensagem processada | conversa={} | modelo={} | tokens_in={} | tokens_out={}",
        id_conversa,
        modelo_usado,
        tokens_entrada,
        tokens_saida,
    )
