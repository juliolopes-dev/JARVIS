"""
Servico WhatsApp Modo 1 — Observador.

Pipeline ao receber webhook MESSAGES_UPSERT:
  1. Validar apikey do header (constant-time)
  2. Filtrar fromMe=true (mensagens enviadas pelo proprio Julio)
  3. Filtrar mensagens de grupo (groupsIgnore=true na Evolution ja filtra na origem,
     mas guardamos defensiva por seguranca)
  4. Identificar Pessoa pelo numero. Se nao monitorada => ignora silenciosamente
  5. Extrair texto (texto direto ou audio transcrito via Whisper)
  6. Garantir Conversa unica daquele contato
  7. Inserir Mensagem(papel="user")
  8. Rodar pipeline existente: Mem0 + 4 parsers NLP
  9. Eventos detectados ganham pessoas_envolvidas=[id_pessoa]
 10. Score de urgencia alto => Web Push opcional

Modo 1 NUNCA chama client.send_text(). E somente leitura.
"""

import asyncio
import secrets
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.modules.auth.models import Usuario
from app.modules.chat.models import Conversa, Mensagem
from app.modules.ia import service as ia_service
from app.modules.memoria import service as memoria_service
from app.modules.memoria.models import Pessoa


# ─── Constantes ──────────────────────────────────────────────────────────────

# TTL do cache de IDs de mensagem (deduplicacao do webhook) — 24h
TTL_DEDUP_SEGUNDOS = 24 * 60 * 60

# Palavras-chave para deteccao de urgencia — TUDO SEM ACENTO.
# Comparacao em calcular_score_urgencia normaliza o texto recebido sem acento.
PALAVRAS_URGENCIA = (
    "urgente", "urgencia", "emergencia",
    "agora", "imediato", "imediatamente", "agora mesmo", "rapido",
    "socorro", "ajuda", "preciso agora", "asap",
)


# ─── Validacao do webhook ────────────────────────────────────────────────────

# Ranges de IP da rede interna do Docker/EasyPanel.
# Webhook so aceita requisicoes vindas desses ranges (containers da mesma VPS).
_IP_PRIVADOS_PREFIXOS = ("10.", "172.", "192.168.", "127.")


def validar_apikey(apikey_recebida: str | None) -> bool:
    """Compara apikey do header contra EVOLUTION_WEBHOOK_SECRET (constant-time)."""
    if not apikey_recebida or not settings.evolution_webhook_secret:
        return False
    return secrets.compare_digest(apikey_recebida, settings.evolution_webhook_secret)


def ip_eh_rede_interna(ip: str | None) -> bool:
    """True se o IP esta em range privado (Docker/VPS interna)."""
    if not ip:
        return False
    return any(ip.startswith(p) for p in _IP_PRIVADOS_PREFIXOS)


def validar_origem_webhook(
    apikey_recebida: str | None,
    instancia_payload: str | None,
    ip_origem: str | None,
) -> tuple[bool, str]:
    """
    Valida se o webhook veio de uma origem confiavel.

    Aceita SE:
      a) header `apikey` bate com EVOLUTION_WEBHOOK_SECRET (caminho preferido), OU
      b) IP de origem e da rede interna (10.*, 172.*, 192.168.*) E
         instancia no payload bate com EVOLUTION_INSTANCE_NAME

    A condicao (b) cobre o caso da Evolution v2 que NAO envia header `apikey`
    quando configurada via WEBHOOK_GLOBAL_URL (comportamento da v2.3.x).

    Retorna (valido, motivo).
    """
    # Caminho A: header apikey (validacao forte)
    if validar_apikey(apikey_recebida):
        return True, "apikey_header"

    # Caminho B: rede interna + instancia esperada
    if not ip_eh_rede_interna(ip_origem):
        return False, f"ip_externo:{ip_origem}"

    if not settings.evolution_instance_name:
        return False, "instance_name_nao_configurado"

    if instancia_payload != settings.evolution_instance_name:
        return False, f"instancia_diferente:{instancia_payload}"

    return True, "rede_interna+instancia"


# ─── Deduplicacao de eventos ────────────────────────────────────────────────

async def ja_processado(message_id: str) -> bool:
    """Retorna True se a mensagem ja foi processada (evita reentrancia do webhook)."""
    if not message_id:
        return False
    try:
        r = await get_redis()
        chave = f"whatsapp:msg:{message_id}"
        # SETNX retorna 1 se gravou (era nova), 0 se ja existia
        gravou = await r.set(chave, "1", nx=True, ex=TTL_DEDUP_SEGUNDOS)
        return not gravou
    except Exception as e:
        logger.warning("Falha no cache de dedup (deixa passar): {}", str(e))
        return False


# ─── Identificacao de contato ───────────────────────────────────────────────

def normalizar_numero(remote_jid: str) -> str | None:
    """
    Extrai o numero puro do remoteJid da Evolution.

    Exemplos:
      "5588981504634@s.whatsapp.net" -> "5588981504634"
      "5588981504634@c.us"           -> "5588981504634"
      "120363xyz@g.us"               -> None (grupo)
      "status@broadcast"             -> None
    """
    if not remote_jid:
        return None
    if "@g.us" in remote_jid or "@broadcast" in remote_jid:
        return None
    numero = remote_jid.split("@")[0].strip()
    # Limpar caracteres invalidos (Evolution as vezes manda sufixos como ":12")
    numero = numero.split(":")[0]
    if not numero.isdigit() or len(numero) < 8:
        return None
    return numero


async def buscar_pessoa_monitorada(
    numero: str, id_usuario: uuid.UUID, db: AsyncSession
) -> Pessoa | None:
    """Retorna a Pessoa SE estiver com flg_monitorar_whatsapp=true."""
    result = await db.execute(
        select(Pessoa).where(
            Pessoa.id_usuario == id_usuario,
            Pessoa.numero_whatsapp == numero,
            Pessoa.flg_monitorar_whatsapp == True,  # noqa: E712
            Pessoa.flg_ativo == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ─── Extracao de conteudo ───────────────────────────────────────────────────

def extrair_texto_da_mensagem(message: dict[str, Any]) -> tuple[str | None, str]:
    """
    Identifica o tipo da mensagem e retorna (texto, tipo).

    Tipos retornados:
      "text"      — mensagem de texto comum (texto direto)
      "audio"     — mensagem de audio (texto vazio, precisa baixar+transcrever)
      "image"     — imagem (texto = caption, se houver)
      "video"     — video (texto = caption, se houver)
      "sticker"   — figurinha (texto = "[figurinha]")
      "document"  — documento (texto = nome do arquivo)
      "outro"     — qualquer outro tipo (ignorado pelo pipeline IA)
    """
    if not message:
        return None, "outro"

    # Texto puro (mensagem mais comum)
    if "conversation" in message:
        return (message.get("conversation") or "").strip(), "text"

    if "extendedTextMessage" in message:
        ext = message["extendedTextMessage"] or {}
        return (ext.get("text") or "").strip(), "text"

    # Audio (PTT — push-to-talk — ou audio normal)
    if "audioMessage" in message:
        return None, "audio"  # texto sera preenchido apos Whisper

    # Imagem com legenda
    if "imageMessage" in message:
        img = message["imageMessage"] or {}
        cap = (img.get("caption") or "").strip()
        return (cap or "[imagem]"), "image"

    # Video com legenda
    if "videoMessage" in message:
        vid = message["videoMessage"] or {}
        cap = (vid.get("caption") or "").strip()
        return (cap or "[video]"), "video"

    if "stickerMessage" in message:
        return "[figurinha]", "sticker"

    if "documentMessage" in message:
        doc = message["documentMessage"] or {}
        nome = doc.get("fileName") or "arquivo"
        return f"[documento: {nome}]", "document"

    return None, "outro"


# ─── Score de urgencia ──────────────────────────────────────────────────────

def _sem_acento(texto: str) -> str:
    """Remove acentos — Julio e contatos as vezes digitam sem acento ('voce', 'esta')."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def calcular_score_urgencia(texto: str) -> int:
    """
    Heuristica simples — retorna pontuacao 0..N.
    Score >= 2 dispara Web Push.

    Sinais:
      - palavra de urgencia: +2
      - 2+ pontos de exclamacao: +1
      - texto majoritariamente em CAPS (+5 letras): +1
      - texto comeca com pergunta direta: +1

    Tudo comparado SEM acento — "voce" e "voce" sao tratados igual,
    mesmo se o contato digita errado em portugues.
    """
    if not texto:
        return 0
    txt_norm = _sem_acento(texto.lower())
    score = 0

    if any(p in txt_norm for p in PALAVRAS_URGENCIA):
        score += 2

    if texto.count("!") >= 2:
        score += 1

    letras = [c for c in texto if c.isalpha()]
    if len(letras) >= 5:
        caps = sum(1 for c in letras if c.isupper())
        if caps / len(letras) >= 0.7:
            score += 1

    # Pergunta direta — comparado sem acento ("voce" casa "voce" e "voce")
    if texto.strip().endswith("?") and any(
        txt_norm.startswith(p)
        for p in ("voce ", "vc ", "tu ", "pode ", "consegue ", "tem ", "ta ", "esta ")
    ):
        score += 1

    return score


# ─── Conversa por contato ───────────────────────────────────────────────────

async def garantir_conversa_whatsapp(
    pessoa: Pessoa, db: AsyncSession
) -> Conversa:
    """
    Retorna a Conversa unica daquele contato WhatsApp, criando se necessario.
    Identificada por metadados.tipo='whatsapp' + metadados.id_pessoa.
    """
    from sqlalchemy import text

    # Busca conversa existente com metadados.id_pessoa = id da pessoa
    result = await db.execute(
        text("""
            SELECT id FROM conversas
            WHERE id_usuario = :id_usuario
              AND flg_ativa = true
              AND (
                titulo = :titulo
                OR titulo LIKE 'WhatsApp:%'
              )
            ORDER BY criado_em DESC
            LIMIT 50
        """),
        {"id_usuario": str(pessoa.id_usuario), "titulo": f"WhatsApp: {pessoa.nome}"},
    )
    rows = result.fetchall()

    # Reusa por titulo exato (mais simples e confiavel que JSONB lookup)
    titulo_alvo = f"WhatsApp: {pessoa.nome}"
    for row in rows:
        conv_result = await db.execute(
            select(Conversa).where(Conversa.id == row[0])
        )
        conv = conv_result.scalar_one_or_none()
        if conv and conv.titulo == titulo_alvo:
            return conv

    # Nao achou — cria nova
    conversa = Conversa(
        id_usuario=pessoa.id_usuario,
        titulo=titulo_alvo,
    )
    db.add(conversa)
    await db.flush()
    logger.info(
        "Conversa WhatsApp criada | pessoa={} | numero={} | conversa={}",
        pessoa.nome, pessoa.numero_whatsapp, conversa.id,
    )
    return conversa


# ─── Pipeline NLP (parsers + Mem0 + eventos) ────────────────────────────────

async def reescrever_em_terceira_pessoa(texto: str, pessoa: Pessoa) -> str:
    """
    Reescreve uma mensagem do contato em terceira pessoa, com nome explicito.

    Sem isso, o Mem0 le "estou com gripe" e salva como fato do USUARIO
    (Julio), nao do contato. Reescrever para "NEXUS esta com gripe" garante
    que o Mem0 associa o fato a pessoa certa.

    Em caso de falha, devolve fallback simples: "<nome> disse: <texto>".
    """
    try:
        cliente = ia_service.get_openai()
        relacao = f" ({pessoa.relacao})" if pessoa.relacao else ""
        resp = await cliente.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Voce reescreve mensagens em terceira pessoa, mantendo o significado. "
                        "Substitua eu/me/meu/minha pelo nome da pessoa que mandou a mensagem. "
                        "Mantenha tom natural e objetivo. Responda APENAS o texto reescrito."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Pessoa: {pessoa.nome}{relacao}\n"
                        f"Mensagem original: {texto}\n\n"
                        f"Reescreva em terceira pessoa, comecando com o nome da pessoa."
                    ),
                },
            ],
            max_tokens=200,
            temperature=0,
        )
        reescrito = (resp.choices[0].message.content or "").strip()
        if not reescrito:
            return f"{pessoa.nome} disse: {texto}"
        return reescrito
    except Exception as e:
        logger.warning("Falha ao reescrever em 3a pessoa: {}", str(e))
        return f"{pessoa.nome} disse: {texto}"


async def processar_texto_whatsapp(
    texto: str,
    pessoa: Pessoa,
    id_usuario: uuid.UUID,
) -> dict[str, Any]:
    """
    Roda o pipeline NLP completo num texto recebido via WhatsApp.

    Acoes possiveis:
      - Mem0 extrai fatos (em 3a pessoa) -> memorias
      - Parser detectar_evento -> eventos com pessoas_envolvidas=[pessoa.id]
      - Parser detectar_lembrete -> lembretes
      - Parser detectar_tarefa -> checklist
      - Parser detectar_tarefa_recorrente -> tarefas_agendadas

    Os parsers (lembrete/tarefa/recorrente/evento) usam o cabecalho
    "[Mensagem de X via WhatsApp]" porque entendem o formato.
    O Mem0 recebe a versao em terceira pessoa para nao confundir o fato
    do contato com fato do usuario do sistema.

    Retorna dict com o que foi criado (para log).
    """
    contexto = f"[Mensagem de {pessoa.nome}"
    if pessoa.relacao:
        contexto += f" ({pessoa.relacao})"
    contexto += " via WhatsApp]"
    texto_com_contexto = f"{contexto}\n{texto}"

    resultado = {"memorias": False, "evento": None, "lembrete": None,
                 "tarefa": None, "recorrente": None}

    # Roda 4 parsers em paralelo (com o contexto do cabecalho)
    try:
        lembrete_info, tarefa_info, recorrente_info, evento_info = await asyncio.gather(
            ia_service.detectar_lembrete(texto_com_contexto),
            ia_service.detectar_tarefa(texto_com_contexto),
            ia_service.detectar_tarefa_recorrente(texto_com_contexto),
            ia_service.detectar_evento(texto_com_contexto),
        )
    except Exception as e:
        logger.warning("Falha nos parsers WhatsApp: {}", str(e))
        lembrete_info = tarefa_info = recorrente_info = evento_info = None

    # Mesma prioridade do chat: recorrente > lembrete > tarefa
    if recorrente_info:
        lembrete_info = None
    if tarefa_info or recorrente_info:
        evento_info = None

    # ── Mem0 (background, nao bloqueia) ──────────────────────────────────
    # Reescreve em 3a pessoa antes de mandar pro Mem0 — assim o fato fica
    # associado a pessoa, nao ao usuario do sistema.
    async def _mem0_background():
        async with AsyncSessionLocal() as sess:
            try:
                texto_3a_pessoa = await reescrever_em_terceira_pessoa(texto, pessoa)
                logger.info(
                    "Mem0 WhatsApp | original={!r} | reescrito={!r}",
                    texto[:80], texto_3a_pessoa[:80],
                )
                await memoria_service.extrair_e_salvar_memoria(
                    texto_3a_pessoa, id_usuario, sess
                )
                await sess.commit()
            except Exception as e:
                await sess.rollback()
                logger.warning("Mem0 WhatsApp falhou: {}", str(e))

    asyncio.create_task(_mem0_background())
    resultado["memorias"] = True

    # ── Evento — sempre vincula a pessoa ─────────────────────────────────
    if evento_info:
        try:
            from datetime import timedelta
            from app.modules.memoria.schemas import EventoCreate

            brt = ZoneInfo("America/Sao_Paulo")
            quando_raw = (evento_info.get("quando") or "hoje").lower()
            agora_brt = datetime.now(brt)
            if quando_raw == "ontem":
                dat_ocorreu = agora_brt - timedelta(days=1)
            elif quando_raw == "hoje":
                dat_ocorreu = agora_brt
            elif quando_raw == "amanha":
                dat_ocorreu = agora_brt + timedelta(days=1)
            else:
                try:
                    dat_ocorreu = datetime.fromisoformat(quando_raw)
                    if dat_ocorreu.tzinfo is None:
                        dat_ocorreu = dat_ocorreu.replace(tzinfo=brt)
                except ValueError:
                    dat_ocorreu = agora_brt

            lojas = evento_info.get("lojas") or None
            if isinstance(lojas, list) and len(lojas) == 0:
                lojas = None

            async with AsyncSessionLocal() as sess:
                dados = EventoCreate(
                    dat_ocorreu=dat_ocorreu,
                    resumo=evento_info["resumo"],
                    categoria=evento_info.get("categoria", "outro"),
                    lojas=lojas,
                    pessoas_envolvidas=[pessoa.id],
                )
                evt = await memoria_service.criar_evento(dados, id_usuario, sess)
                await sess.commit()
                resultado["evento"] = str(evt.id)
        except Exception as e:
            logger.warning("Falha ao criar evento WhatsApp: {}", str(e))

    # ── Lembrete ──────────────────────────────────────────────────────────
    if lembrete_info:
        try:
            from app.modules.lembretes.schemas import LembreteCreate
            from app.modules.lembretes.service import criar_lembrete

            dat_lembrete = datetime.fromisoformat(lembrete_info["dat_lembrete"])
            descricao_orig = lembrete_info.get("descricao") or ""
            descricao = f"[{pessoa.nome}] {descricao_orig}".strip()

            async with AsyncSessionLocal() as sess:
                dados = LembreteCreate(
                    titulo=lembrete_info["titulo"],
                    descricao=descricao,
                    dat_lembrete=dat_lembrete,
                )
                lem = await criar_lembrete(dados, id_usuario, sess)
                await sess.commit()
                resultado["lembrete"] = str(lem.id)
        except Exception as e:
            logger.warning("Falha ao criar lembrete WhatsApp: {}", str(e))

    # ── Tarefa de checklist ───────────────────────────────────────────────
    if tarefa_info:
        try:
            from app.modules.checklist.schemas import TarefaCreate
            from app.modules.checklist.service import buscar_ou_criar_lista, criar_tarefa

            dat_vencimento = None
            if tarefa_info.get("dat_vencimento"):
                dat_vencimento = datetime.fromisoformat(tarefa_info["dat_vencimento"])

            async with AsyncSessionLocal() as sess:
                id_lista = await buscar_ou_criar_lista(
                    tarefa_info.get("nome_lista"), id_usuario, sess
                )
                dados = TarefaCreate(
                    titulo=tarefa_info["titulo"],
                    descricao=f"[{pessoa.nome}] {tarefa_info.get('descricao') or ''}".strip(),
                    prioridade=tarefa_info.get("prioridade", "media"),
                    dat_vencimento=dat_vencimento,
                    id_lista=id_lista,
                )
                tar = await criar_tarefa(dados, id_usuario, sess)
                await sess.commit()
                resultado["tarefa"] = str(tar.id)
        except Exception as e:
            logger.warning("Falha ao criar tarefa WhatsApp: {}", str(e))

    # ── Tarefa recorrente ─────────────────────────────────────────────────
    if recorrente_info:
        try:
            from app.modules.tarefas.schemas import TarefaAgendadaCreate
            from app.modules.tarefas.service import criar_tarefa as criar_recorrente

            async with AsyncSessionLocal() as sess:
                dados = TarefaAgendadaCreate(
                    descricao=recorrente_info["descricao"],
                    cron_expressao=recorrente_info["cron_expressao"],
                    parametros={
                        "texto_push": recorrente_info.get(
                            "texto_push", recorrente_info["descricao"]
                        ),
                        "titulo_push": "🔔 " + recorrente_info["descricao"][:40],
                        "origem": "whatsapp",
                        "id_pessoa": str(pessoa.id),
                    },
                )
                rec = await criar_recorrente(dados, id_usuario, sess)
                await sess.commit()
                resultado["recorrente"] = str(rec.id)
        except Exception as e:
            logger.warning("Falha ao criar recorrente WhatsApp: {}", str(e))

    return resultado


# ─── Web Push de urgencia ───────────────────────────────────────────────────

async def disparar_push_urgencia(
    pessoa: Pessoa, texto: str, id_usuario: uuid.UUID
) -> None:
    """Envia push para todos os dispositivos ativos avisando msg urgente."""
    try:
        from app.core.webpush import enviar_push
        from app.modules.notificacoes.models import SubscricaoPush

        async with AsyncSessionLocal() as sess:
            result = await sess.execute(
                select(SubscricaoPush).where(
                    SubscricaoPush.id_usuario == id_usuario,
                    SubscricaoPush.flg_ativo == True,  # noqa: E712
                )
            )
            subs = result.scalars().all()

            if not subs:
                return

            payload = {
                "title": f"🚨 {pessoa.nome}",
                "body": texto[:120],
                "url": "/memoria",
            }
            for sub in subs:
                ok = enviar_push(sub.endpoint, sub.chave_p256dh, sub.chave_auth, payload)
                if not ok:
                    sub.flg_ativo = False
                    sess.add(sub)
            await sess.commit()
    except Exception as e:
        logger.warning("Falha ao disparar push de urgencia: {}", str(e))


# ─── Contadores em Redis ────────────────────────────────────────────────────

async def incrementar_contador_dia() -> None:
    """Incrementa contador de mensagens recebidas hoje (BRT)."""
    try:
        brt = ZoneInfo("America/Sao_Paulo")
        hoje = datetime.now(brt).strftime("%Y-%m-%d")
        r = await get_redis()
        chave = f"whatsapp:contador:{hoje}"
        await r.incr(chave)
        await r.expire(chave, 60 * 60 * 36)  # 36h pra cobrir virada de dia
    except Exception as e:
        logger.debug("Falha ao incrementar contador: {}", str(e))


async def get_contador_hoje() -> int:
    try:
        brt = ZoneInfo("America/Sao_Paulo")
        hoje = datetime.now(brt).strftime("%Y-%m-%d")
        r = await get_redis()
        valor = await r.get(f"whatsapp:contador:{hoje}")
        return int(valor) if valor else 0
    except Exception:
        return 0


# ─── Pegar usuario unico do sistema ─────────────────────────────────────────

async def get_usuario_unico(db: AsyncSession) -> Usuario | None:
    """
    Jarvis e single-user. Retorna o primeiro usuario ativo do sistema.
    Toda mensagem WhatsApp recebida pertence a este usuario.
    """
    result = await db.execute(
        select(Usuario).where(Usuario.flg_ativo == True).limit(1)  # noqa: E712
    )
    return result.scalar_one_or_none()


# ─── Handler principal do webhook ───────────────────────────────────────────

async def processar_webhook_messages_upsert(
    payload: dict[str, Any], db: AsyncSession
) -> dict[str, Any]:
    """
    Handler do evento MESSAGES_UPSERT da Evolution.

    Retorna dict com o resultado para log/debug:
      {"acao": "ignorada"|"processada", "motivo": str, "id_pessoa": str|None}
    """
    data = payload.get("data") or {}

    # Estrutura da Evolution v2: data pode ser objeto unico ou {messages: [...]}
    # MESSAGES_UPSERT geralmente vem com 1 mensagem em data direto.
    key = data.get("key") or {}
    message = data.get("message") or {}
    message_id = key.get("id", "")
    from_me = key.get("fromMe", False)
    remote_jid = key.get("remoteJid", "")

    # ── Filtros iniciais ────────────────────────────────────────────────
    if from_me:
        return {"acao": "ignorada", "motivo": "fromMe=true"}

    if await ja_processado(message_id):
        return {"acao": "ignorada", "motivo": "duplicada", "message_id": message_id}

    numero = normalizar_numero(remote_jid)
    if not numero:
        return {"acao": "ignorada", "motivo": "grupo_ou_broadcast", "remote_jid": remote_jid}

    # ── Identificar usuario do sistema ─────────────────────────────────
    usuario = await get_usuario_unico(db)
    if not usuario:
        logger.warning("Nenhum usuario ativo no sistema — ignorando mensagem WhatsApp")
        return {"acao": "ignorada", "motivo": "sem_usuario"}

    # ── Whitelist por pessoa ───────────────────────────────────────────
    pessoa = await buscar_pessoa_monitorada(numero, usuario.id, db)
    if not pessoa:
        logger.debug("Numero nao monitorado | numero={}", numero)
        return {"acao": "ignorada", "motivo": "nao_monitorado", "numero": numero}

    # ── Extrair conteudo ───────────────────────────────────────────────
    texto, tipo = extrair_texto_da_mensagem(message)

    if tipo == "audio":
        from app.modules.whatsapp.audio import transcrever_audio_whatsapp
        texto = await transcrever_audio_whatsapp(message)
        if not texto:
            texto = "[audio nao transcrito]"

    if not texto:
        return {"acao": "ignorada", "motivo": "sem_conteudo", "tipo": tipo}

    # ── Garantir conversa + salvar mensagem ────────────────────────────
    conversa = await garantir_conversa_whatsapp(pessoa, db)
    msg = Mensagem(
        id_conversa=conversa.id,
        papel="user",
        conteudo=texto,
    )
    db.add(msg)
    await db.flush()
    await db.commit()

    # ── Contador (best-effort) ─────────────────────────────────────────
    asyncio.create_task(incrementar_contador_dia())

    # ── Pipeline NLP ───────────────────────────────────────────────────
    # So roda em texto/audio (nao em figurinha/imagem sem caption)
    if tipo in ("text", "audio") or (tipo in ("image", "video") and len(texto) > 5 and not texto.startswith("[")):
        resultado_nlp = await processar_texto_whatsapp(texto, pessoa, usuario.id)
    else:
        resultado_nlp = {"memorias": False, "ignorado_pipeline": True}

    # ── Push de urgencia ───────────────────────────────────────────────
    score = calcular_score_urgencia(texto)
    if score >= 2:
        asyncio.create_task(disparar_push_urgencia(pessoa, texto, usuario.id))
        resultado_nlp["push_urgencia"] = True
        resultado_nlp["score"] = score

    logger.info(
        "WhatsApp processado | pessoa={} | tipo={} | texto={} | resultado={}",
        pessoa.nome, tipo, texto[:80], resultado_nlp,
    )
    return {
        "acao": "processada",
        "id_pessoa": str(pessoa.id),
        "tipo": tipo,
        "id_mensagem": str(msg.id),
        **resultado_nlp,
    }


async def processar_webhook_connection_update(payload: dict[str, Any]) -> dict[str, Any]:
    """Handler do evento CONNECTION_UPDATE — apenas log + cache do estado."""
    data = payload.get("data") or {}
    state = data.get("state", "unknown")
    logger.info("WhatsApp connection_update | state={} | data={}", state, data)
    try:
        r = await get_redis()
        await r.setex("whatsapp:state", 60 * 60, state)
    except Exception:
        pass
    return {"acao": "registrada", "state": state}
