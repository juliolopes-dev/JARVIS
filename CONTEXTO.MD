# Jarvis — Assistente Pessoal de IA
> Memoria viva. Atualizado automaticamente apos qualquer mudanca e antes de encerrar cada sessao.

## Objetivo
Assistente pessoal inteligente inspirado no Jarvis do Homem de Ferro. Conversa por voz ou texto, aprende com tudo que o usuario fala, executa tarefas de forma autonoma e mantem o usuario informado proativamente. Acessivel de qualquer dispositivo via PWA.

**Publico-alvo:** Julio — uso pessoal, um unico usuario.

## Usuarios e Perfis
- **Usuario unico (Julio)** — dono do sistema, acesso total a todas as funcionalidades
- Sem hierarquia de permissoes ou multi-tenant — simplicidade maxima

## Regras de Negocio
- **Memoria persistente permanente** — Jarvis lembra de tudo que foi dito, nunca "esquece" sem comando explicito
- **Roteamento inteligente de modelos** — Claude para raciocinio/contexto longo, GPT-4o mini para tarefas simples e baratas
- **Fallback obrigatorio** — se Claude falhar, cair automaticamente para GPT-4o mini
- **Briefing diario automatico** — todo dia no horario configurado, Jarvis envia agenda + e-mails + tarefas resumidos
- **Tarefas recorrentes por linguagem natural** — "Jarvis, todo dia as 8h me manda as noticias desse site" vira um job agendado
- **Memoria de pessoas** — mencionar alguem uma vez guarda contexto para sempre
- **Notificacoes proativas** — Jarvis avisa sem ser perguntado quando algo importante acontece
- **Rastreabilidade de custo** — toda mensagem registra modelo usado, tokens de entrada e saida

## Stack
- **Frontend:** React + Vite + TypeScript + Tailwind CSS | Libs: axios, zustand, @tanstack/react-query, lucide-react, date-fns, sonner, vite-plugin-pwa, react-markdown, motion
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL | Libs: uvicorn, asyncpg, redis, anthropic, openai, mem0ai, pgvector, httpx, python-jose[cryptography], passlib[bcrypt], pydantic-settings, slowapi, loguru, apscheduler, pywebpush, elevenlabs, python-multipart
- **Auth:** JWT com `python-jose + passlib` — token 10h + refresh token 30 dias. Usuario unico, sem OAuth social
- **Logs:** Loguru (JSON em producao, colorido em dev) com rotacao automatica, filter para nao logar chaves API
- **Seguranca:** CORS explicito (nunca `*`), Rate Limiting via slowapi (5 tent/min em `/api/auth/login`), Pydantic v2 validation em todos os schemas
- **Cache/Contexto rapido:** Redis com AOF persistente — contexto da conversa atual
- **IA:** Claude API (raciocinio), GPT-4o (simples/fallback), Whisper-1 (transcricao audio — JA ATIVO), ElevenLabs (Fase 5), Claude Vision (Fase 5), Embeddings OpenAI text-embedding-3-small (1536 dim)
- **Memoria:** Mem0 (auto-extracao de fatos) + pgvector (busca semantica) + PostgreSQL (historico completo)
- **Tarefas agendadas:** APScheduler com SQLAlchemyJobStore (jobs persistidos no banco)
- **Notificacoes:** Web Push Notifications via pywebpush + VAPID keys
- **Gerenciador:** uv | Linting: Ruff
- **MCP:** Mem0 (memoria), Gmail (Fase 4), Google Calendar (Fase 4), Web Search (Fase 4)
- **Infra:** VPS + EasyPanel | Deploy: push GitHub -> auto deploy | Timezone: America/Sao_Paulo

## Banco de Dados

### Tabelas (nomes em Portugues com prefixos obrigatorios)

**Modulo auth:**
- `usuarios` — id (UUID PK), cod_usuario, nome, email (unique), senha_hash, flg_ativo, criado_em, atualizado_em

**Modulo chat:**
- `conversas` — id (UUID PK), id_usuario (FK), titulo, flg_ativa, criado_em, atualizado_em
- `mensagens` — id (UUID PK), id_conversa (FK), papel ('user'/'assistant'/'system'), conteudo (TEXT), modelo_usado, tokens_entrada, tokens_saida, criado_em

**Modulo memoria:**
- `memorias` — id (UUID PK), id_usuario (FK), id_mem0 (unique), conteudo (TEXT), categoria, embedding (Vector 1536), metadados (JSONB), flg_ativo, criado_em, atualizado_em
- `pessoas` — id (UUID PK), id_usuario (FK), cod_pessoa, nome, relacao, notas, metadados (JSONB), flg_ativo, criado_em, atualizado_em

**Modulo tarefas (Fase 3):**
- `tarefas_agendadas` — id (UUID PK), id_usuario (FK), descricao, tipo ('briefing'/'monitoramento'/'lembrete'), cron_expressao, parametros (JSONB), sts_tarefa, dat_ultima_execucao, dat_proxima_execucao, criado_em, atualizado_em

**Modulo notificacoes (Fase 3):**
- `subscricoes_push` — id (UUID PK), id_usuario (FK), endpoint, chave_p256dh, chave_auth, dispositivo, flg_ativo, criado_em

**Modulo config:**
- `configuracoes` — id (UUID PK), id_usuario (FK unique), modelo_preferido, tema, voz_resposta, flg_briefing_diario, horario_briefing, flg_notificacoes, preferencias (JSONB), criado_em, atualizado_em

**Modulo livros (Fase 3):**
- `livros` — id (UUID PK), id_usuario (FK), titulo, autor, total_paginas, total_chunks, flg_ativo, dat_upload
- `livro_chunks` — id (UUID PK), id_livro (FK CASCADE), numero, capitulo, conteudo (TEXT), total_palavras
- `leitura_progresso` — id (UUID PK), id_livro (FK CASCADE unique), chunk_atual, tamanho_chunk, flg_modo_estudo, flg_concluido, dat_ultimo_acesso, dat_conclusao

### Indices
- `ix_conversas_id_usuario`, `ix_mensagens_id_conversa`, `ix_mensagens_criado_em`
- `ix_memorias_id_usuario`, `ix_memorias_categoria`, indice HNSW em `memorias.embedding` para busca vetorial
- `ix_pessoas_id_usuario`, `ix_tarefas_sts_tarefa`

### Modelos SQLAlchemy Completos e Atualizados

```python
# ===== app/modules/auth/models.py =====
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cod_usuario: Mapped[int] = mapped_column(Integer, autoincrement=True, unique=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversas: Mapped[list["Conversa"]] = relationship(back_populates="usuario")
    memorias: Mapped[list["Memoria"]] = relationship(back_populates="usuario")
    pessoas: Mapped[list["Pessoa"]] = relationship(back_populates="usuario")


# ===== app/modules/chat/models.py =====
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    titulo: Mapped[str | None] = mapped_column(String(200))
    flg_ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="conversas")
    mensagens: Mapped[list["Mensagem"]] = relationship(back_populates="conversa", order_by="Mensagem.criado_em")


class Mensagem(Base):
    __tablename__ = "mensagens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_conversa: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversas.id"), index=True)
    papel: Mapped[str] = mapped_column(String(20))
    conteudo: Mapped[str] = mapped_column(Text)
    modelo_usado: Mapped[str | None] = mapped_column(String(50))
    tokens_entrada: Mapped[int | None] = mapped_column(Integer)
    tokens_saida: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    conversa: Mapped["Conversa"] = relationship(back_populates="mensagens")


# ===== app/modules/memoria/models.py =====
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Memoria(Base):
    __tablename__ = "memorias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    id_mem0: Mapped[str | None] = mapped_column(String(100), unique=True)
    conteudo: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(50), index=True)
    embedding = mapped_column(Vector(1536))
    metadados: Mapped[dict | None] = mapped_column(JSONB)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="memorias")


class Pessoa(Base):
    __tablename__ = "pessoas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    cod_pessoa: Mapped[int] = mapped_column(autoincrement=True, unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    relacao: Mapped[str | None] = mapped_column(String(100))
    notas: Mapped[str | None] = mapped_column(Text)
    metadados: Mapped[dict | None] = mapped_column(JSONB)
    flg_ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="pessoas")
```

### Migracoes Alembic
- A primeira migracao DEVE executar `CREATE EXTENSION IF NOT EXISTS vector;` antes de criar tabelas
- Criar indice HNSW em `memorias.embedding` manualmente na migracao: `CREATE INDEX ON memorias USING hnsw (embedding vector_cosine_ops);`

### Decisoes importantes
- **Tabelas de Fase 3 ja modeladas na Fase 1** — evita migracoes complexas depois
- **Embedding dim 1536** — OpenAI `text-embedding-3-small` (melhor custo/beneficio)
- **id_mem0 na tabela memorias** — sincronizacao bidirecional com o Mem0
- **Soft delete universal** (`flg_ativo`) — nunca perder dados
- **tokens_entrada e tokens_saida por mensagem** — rastreabilidade de custo de IA
- **metadados JSONB** — flexibilidade sem alterar schema

## Rotas da API

| Metodo | Rota | Descricao | Auth |
|--------|------|-----------|------|
| POST | `/api/auth/registrar` | Criar conta (uso unico — setup) | ❌ |
| POST | `/api/auth/login` | Login → JWT + refresh token | ❌ |
| POST | `/api/auth/refresh` | Renovar JWT | ❌ |
| GET | `/api/auth/me` | Dados do usuario logado | ✅ |
| PUT | `/api/auth/senha` | Alterar senha | ✅ |
| POST | `/api/chat/conversas` | Criar nova conversa | ✅ |
| GET | `/api/chat/conversas` | Listar conversas (paginado) | ✅ |
| GET | `/api/chat/conversas/{id}` | Detalhes + mensagens | ✅ |
| DELETE | `/api/chat/conversas/{id}` | Arquivar (soft delete) | ✅ |
| POST | `/api/chat/conversas/{id}/mensagens` | Enviar mensagem → SSE streaming | ✅ |
| GET | `/api/chat/conversas/{id}/mensagens` | Historico paginado | ✅ |
| GET | `/api/memoria/buscar` | Busca semantica (query param `q`) | ✅ |
| GET | `/api/memoria` | Listar memorias (filtro por categoria) | ✅ |
| DELETE | `/api/memoria/{id}` | Desativar memoria | ✅ |
| GET | `/api/memoria/pessoas` | Listar pessoas | ✅ |
| GET | `/api/memoria/pessoas/{id}` | Detalhes de pessoa | ✅ |
| POST | `/api/memoria/pessoas` | Criar pessoa | ✅ |
| PUT | `/api/memoria/pessoas/{id}` | Atualizar pessoa | ✅ |
| DELETE | `/api/memoria/pessoas/{id}` | Desativar pessoa | ✅ |
| GET | `/api/config` | Obter configuracoes | ✅ |
| PUT | `/api/config` | Atualizar configuracoes | ✅ |
| GET | `/api/livros` | Listar livros | ✅ |
| POST | `/api/livros` | Upload PDF (multipart, max 50MB) | ✅ |
| DELETE | `/api/livros/{id}` | Remover livro (soft delete) | ✅ |
| GET | `/api/livros/{id}/ler/proximo` | Proximo chunk + avanca ponteiro | ✅ |
| GET | `/api/livros/{id}/ler/anterior` | Chunk anterior + volta ponteiro | ✅ |
| GET | `/api/livros/{id}/progresso` | Obter progresso de leitura | ✅ |
| PATCH | `/api/livros/{id}/progresso` | Atualizar tamanho_chunk + modo_estudo | ✅ |
| GET | `/api/tarefas-agendadas/` | Listar tarefas recorrentes (Fase 3) | ✅ |
| POST | `/api/tarefas-agendadas/` | Criar tarefa recorrente (Fase 3) | ✅ |
| PUT | `/api/tarefas-agendadas/{id}` | Atualizar tarefa (descricao/cron/status) (Fase 3) | ✅ |
| DELETE | `/api/tarefas-agendadas/{id}` | Remover tarefa recorrente (Fase 3) | ✅ |
| POST | `/api/tarefas-agendadas/{id}/executar` | Disparar manualmente (teste) (Fase 3) | ✅ |
| POST | `/api/notificacoes/subscrever` | Registrar push (Fase 3) | ✅ |
| DELETE | `/api/notificacoes/subscrever` | Remover push (Fase 3) | ✅ |
| POST | `/api/notificacoes/testar` | Teste push (Fase 3) | ✅ |
| GET | `/api/health` | Healthcheck | ❌ |
| GET | `/api/version` | Versao do backend | ❌ |

**Total: 40 rotas** | Fase 1: 20 | Fase 2: 2 | Fase 3: 18

## Estrutura de Pastas Atual

```text
jarvis/
├── frontend/
│   ├── public/
│   │   ├── version.json
│   │   ├── manifest.json
│   │   └── sw.js
│   └── src/
│       ├── components/
│       │   ├── ui/
│       │   └── chat/
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── ChatPage.tsx
│       │   ├── MemoriaPage.tsx
│       │   ├── LivrosPage.tsx
│       │   └── ConfigPage.tsx
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useChat.ts
│       │   └── usePushNotification.ts
│       ├── services/
│       │   ├── api.ts
│       │   ├── authService.ts
│       │   ├── chatService.ts
│       │   ├── checklistService.ts
│       │   ├── configService.ts
│       │   ├── lembretesService.ts
│       │   ├── livrosService.ts
│       │   ├── memoriaService.ts
│       │   └── tarefasAgendadasService.ts
│       ├── store/
│       │   └── useAppStore.ts
│       ├── types/
│       ├── utils/
│       │   ├── formatDate.ts
│       │   └── cn.ts
│       ├── App.tsx
│       └── main.tsx
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── deps.py
│   │   │   └── redis.py
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── chat/
│   │   │   ├── memoria/
│   │   │   ├── ia/
│   │   │   │   ├── service.py
│   │   │   │   └── prompts.py
│   │   │   ├── tarefas/
│   │   │   │   ├── models.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── router.py
│   │   │   ├── lembretes/
│   │   │   ├── livros/
│   │   │   ├── checklist/
│   │   │   ├── briefing/
│   │   │   ├── notificacoes/
│   │   │   └── config/
│   │   ├── middleware/
│   │   │   ├── cors.py
│   │   │   └── rate_limit.py
│   │   └── main.py
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── uv.lock
├── Dockerfile
├── .env.example
├── .gitignore
├── CONTEXTO.MD
└── .claude/
    └── CLAUDE.md
```

## Variaveis de Ambiente

```env
# Banco
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/jarvis

# Timezone
TZ=America/Sao_Paulo
PGTZ=America/Sao_Paulo

# Autenticacao
JWT_SECRET=chave_secreta_minimo_32_caracteres
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=600
JWT_REFRESH_EXPIRES_DAYS=30

# Servidor
PORT=8000
ENVIRONMENT=production

# Frontend / CORS
FRONTEND_URL=https://jarvis.seudominio.com.br
CORS_ORIGINS=["https://jarvis.seudominio.com.br"]

# Redis
REDIS_URL=redis://localhost:6379/0

# Logs
LOG_LEVEL=info

# APIs de IA
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Mem0
MEM0_COLLECTION_NAME=jarvis_memories

# ElevenLabs (Fase 5)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# Web Push (Fase 3)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_CLAIMS_EMAIL=
```

## Comandos Uteis
- Dev frontend: `cd frontend && npm run dev`
- Dev backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- Nova migracao: `cd backend && uv run alembic revision --autogenerate -m "descricao"`
- Aplicar migracao: `cd backend && uv run alembic upgrade head`
- Reverter migracao: `cd backend && uv run alembic downgrade -1`
- Build local: `docker build -t jarvis .`
- Gerar VAPID keys (Fase 3): `npx web-push generate-vapid-keys`
- URL producao: https://jarvis.seudominio.com.br
- URL EasyPanel: https://[easypanel-dashboard]

## Integracoes Externas
- **Claude API (Anthropic)** — Cerebro principal: raciocinio, conversas complexas, contexto longo, titulos auto-gerados das conversas
- **OpenAI API** — GPT-4o mini (tarefas simples/baratas, fallback do Claude), Embeddings `text-embedding-3-small` (busca semantica), Whisper (Fase 5)
- **Mem0** — Auto-extracao de fatos das conversas, sincronizado com PostgreSQL
- **ElevenLabs** — Text-to-Speech (Fase 5)
- **Google Calendar MCP** — Agenda (Fase 4)
- **Gmail MCP** — E-mails (Fase 4)
- **Web Search MCP** — Busca em tempo real (Fase 4)
- **Web Push (VAPID)** — Notificacoes proativas no PWA (Fase 3)

## Roadmap
- [x] **Fase 1 — Cerebro:** Setup, Database + Alembic, Redis, Auth JWT, Modulo IA (Claude + GPT-4o + fallback), Modulo Memoria (Mem0 + pgvector), Modulo Chat (SSE streaming), CORS + Rate Limiting, Healthcheck + version.json, Dockerfile + deploy EasyPanel, Loguru
- [x] **Fase 2 — Interface:** Setup frontend Vite, Tela Login, Tela Chat (streaming + auto-scroll), Sidebar Conversas, Tela Memoria, Tela Config, PWA instalavel (SW + manifest + icones), Markdown nas respostas, Design system dark, Layout responsivo mobile
- [x] **Fase 3 — Autonomia:** ✅ APScheduler com SQLAlchemyJobStore, ✅ Web Push VAPID (notificacoes no celular), ✅ Lembretes via chat (NLP) e manual (LembretesPage), ✅ Whisper-1 (audio→texto→envia), ✅ Modulo Livros (upload PDF, chunking, progresso, resumo IA, perguntas estudo, LivrosPage), ✅ Briefing diario (GPT-4o + cron + Web Push + historico), ✅ Modulo Checklist (listas + tarefas com prioridade/vencimento + TarefasPage responsiva), ✅ Tarefas recorrentes por linguagem natural (CronTrigger + parser NLP), ✅ Gerenciamento de tarefas agendadas (aba Recorrentes em LembretesPage)
- [ ] **Fase 4 — Integracoes (FUTURO):** MCP Gmail, MCP Google Calendar, MCP Web Search
- [ ] **Fase 5 — Voz (FUTURO):** ElevenLabs (voz), Claude Vision (imagens)

## Super Assistente — Features do "Jarvis Definitivo"

Lista de 10 features ordenadas por impacto real no dia-a-dia. Serao desenvolvidas aos poucos apos Fase 4.
**Filosofia:** super assistente nao vem de framework (LangChain/etc), vem de mais contexto + mais ferramentas + prompts melhores + dados pessoais. MCP resolve integracoes, SDK direto resolve orquestracao simples.

### Prioridade MAXIMA (caso de uso diario)

#### 1. Gmail MCP (Fase 4 ja prevista)
- Acoes: resumir inbox, responder emails, arquivar newsletters, buscar por remetente/assunto
- Impacto: gigante — email e o maior ladrao de tempo
- Esforco: 2 dias
- Integracao: MCP oficial do Google

#### 2. Google Calendar MCP (Fase 4 ja prevista)
- Acoes: "que compromissos tenho amanha?", "marca reuniao com X quarta 14h"
- Integra com briefing diario ja existente
- Esforco: 1 dia

#### 3. WhatsApp via Evolution API (planejado em 2026-04-25)

**Stack:** Evolution API v2.3.7 self-hosted no EasyPanel (Docker oficial + Postgres/Redis proprios da Evolution, separados do banco do Jarvis). Documentacao: https://doc.evolution-api.com/v2

**Ambiente em producao (confirmado em 2026-04-26):**
- URL: `https://evolution.lopestechhub.com.br` (HTTPS via Let's Encrypt no EasyPanel — destino interno HTTP:8080)
- Versao: 2.3.7
- Instancia ativa: `juliolopes` (numero pessoal do Julio, ja conectada)
- API key da instancia: gerenciada em variavel `.env` (gitignored), NUNCA commitar
- Postgres dedicado: `<project>_evolution-api-db`
- Redis dedicado: `<project>_evolution-api-redis`
- `DEL_INSTANCE=false` (sessao Baileys protegida)
- `WEBHOOK_GLOBAL_ENABLED=true` (sera ativado no setup do Modo 1)
- Webhook global apontando para Jarvis: `https://applications-jarvis.tbs25p.easypanel.host/api/whatsapp/webhook`
- Webhook DA INSTANCIA juliolopes ja existe e aponta para n8n (automacao diaria — NAO MEXER)

**Por que webhook global em vez de webhook da instancia:** a instancia `juliolopes` ja tem webhook configurado para uma automacao do n8n que envia mensagem diaria para um numero. Trocar o webhook da instancia quebraria essa automacao. Webhook global funciona em paralelo — Evolution dispara eventos para AMBOS os destinos (n8n recebe via webhook da instancia, Jarvis recebe via webhook global). Filtro do lado do Jarvis (`fromMe=true` e whitelist `flg_monitorar_whatsapp`) garante que so processa o que interessa.

**Caso de uso:** Julio nao quer "ChatGPT no zap" — quer o Jarvis observando o WhatsApp dele e capturando contexto de contatos especificos (patrao, esposa, familia). Foco em **memoria + eventos automaticos**, nao em conversa bidirecional.

**Numero usado:** o proprio numero do Julio (nao chip novo). Trava: no Modo 1 o Jarvis nunca chama `/message/sendText`, so observa.

**Migrar automacao n8n → Jarvis:** registrado como Fase WhatsApp 2.5 (entre Modo 2 e Grupos). NAO faz parte do escopo Modo 1.

##### Modo 1 — Observador ✅ IMPLEMENTADO E EM PRODUCAO (2026-04-26)

**Validado em producao:** mensagens reais via NEXUS (558981504634) processaram corretamente — Mem0 extraiu fatos vinculados a pessoa, lembrete criado com data/hora correta, push de urgencia disparou. Conversa "WhatsApp: NEXUS" criada e persistida.

**Fixes descobertos durante a validacao em producao (registrados em licoes.md):**

1. **Evolution v2.3 nao envia header `apikey` no webhook global** — solucao: validar por (rede interna 10.x/172.x/192.168.x) + (instance no body bate com EVOLUTION_INSTANCE_NAME). Trafego dentro da VPS nao expoe a webhook publico.
2. **`data` do payload pode ser dict OU list** — Evolution manda dict para messages.upsert mas list para contacts.upsert/chats.upsert. Pydantic com schema rigido quebrava com 500 e Evolution reenviava em loop. Solucao: trabalhar direto com o dict do body, sem validar via Pydantic.
3. **Mem0 salvava fato em primeira pessoa do USUARIO** — "Estou com gripe" virava fato do Julio, nao do contato. Solucao: GPT-4o-mini reescreve em terceira pessoa antes de mandar pro Mem0 ("NEXUS esta com gripe forte").
4. **Lembrete/tarefa criados via WhatsApp ficavam genericos** — `titulo="Consulta medica"` + `descricao="[NEXUS]"` nao permitia IA inferir vinculo. Solucao: nome no titulo (`"Consulta medica (NEXUS)"`) + descricao com mensagem original (`'Mensagem de NEXUS — "Tenho consulta amanha as 14h"'`).

Reaproveita 90% da infra que ja existe — sem tabelas novas para mensagens.

**Fluxo:**
```
Mensagem WhatsApp do contato monitorado
   ↓
Webhook POST /api/whatsapp/webhook (sem JWT, valida apikey da Evolution)
   ↓
Identifica Pessoa pelo numero. Se nao monitorada → ignora silenciosamente
   ↓
Salva como Mensagem (papel="user") na Conversa unica daquele contato
   (titulo="WhatsApp: Patrao Carlos", metadados={tipo:"whatsapp", id_pessoa, numero})
   ↓
Audio? Whisper-1 (ja integrado) transcreve antes
   ↓
Pipeline existente: 4 parsers NLP + Mem0 + extrator de eventos
   - Mem0 → memorias (fatos atemporais)
   - Parser evento → eventos com pessoas_envolvidas=[id_pessoa]
   - Parser lembrete/tarefa/recorrente → lembretes/tarefas se aplicavel
   ↓
Score de urgencia ("urgente", "agora", "?") → Web Push opcional
```

**Mudancas no banco (1 migration pequena):**
- `pessoas`: adicionar `numero_whatsapp VARCHAR(20) UNIQUE`, `flg_monitorar_whatsapp BOOLEAN DEFAULT false`
- Reusar `conversas`/`mensagens` com `metadados.tipo="whatsapp"` — SEM tabela nova

**Modulo novo `backend/app/modules/whatsapp/`:**
- `client.py` — HTTPX client da Evolution (sendText, fetchInstance, setWebhook)
- `service.py` — webhook handler: filtra contato → roda pipeline existente
- `router.py` — `POST /api/whatsapp/webhook` (publica), `GET /api/whatsapp/status` (auth), `POST /api/whatsapp/qrcode` (auth)
- `schemas.py` — payloads Evolution (MESSAGES_UPSERT, CONNECTION_UPDATE)

**Frontend:**
- Pagina `/pessoas` ganha 2 campos: `numero_whatsapp` + toggle `flg_monitorar_whatsapp`
- Nova pagina `/whatsapp` apenas para status da Evolution (conectado/desconectado, QR Code para reconectar, contador do dia)
- Memorias e Eventos da pessoa ja aparecem automaticamente nas paginas existentes — zero UI nova

**Configuracao Evolution na criacao da instancia:**
```json
{
  "instanceName": "jarvis",
  "integration": "WHATSAPP-BAILEYS",
  "groupsIgnore": true,
  "readMessages": false,
  "readStatus": false,
  "alwaysOnline": false,
  "syncFullHistory": false,
  "webhook": {
    "url": "https://jarvis.seudominio.com.br/api/whatsapp/webhook",
    "byEvents": false,
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
  }
}
```

**Variaveis de ambiente novas:**
```env
EVOLUTION_API_URL=https://evolution.seudominio.com.br
EVOLUTION_API_KEY=chave-da-instancia
EVOLUTION_INSTANCE_NAME=jarvis
EVOLUTION_WEBHOOK_SECRET=segredo-para-validar-webhook
```

**Riscos:**
- Ban WhatsApp (Baileys nao-oficial) → flags conservadoras acima + numero pessoal so, sem disparo em massa
- Sessao Baileys perde no restart → backup do banco da Evolution semanal
- Webhook publico → validar `apikey` no header em TODA requisicao

##### Modo 2 — Comandante via "Jarvis,..." (DEPOIS, +1 dia)

Apos Modo 1 estavel. Detecta comando do proprio Julio:

```
Mensagem com fromMe=true E texto.lower().startswith("jarvis,")
   ↓
Tira o "Jarvis," do inicio
   ↓
Manda pro chat existente (modulo chat/service.py) — mesma logica do chat web
   ↓
Resposta do Claude → envia via /message/sendText/{instance} no MESMO numero/chat
```

**UX recomendada:** Julio cria um contato no zap chamado "Jarvis" apontando pro proprio numero (ou usa "mensagens salvas") — assim so processa comando quando ele explicitamente fala com "o Jarvis", nunca em conversa real com outra pessoa.

**Acoes possiveis pelo Modo 2:**
- "Jarvis, anota: comprar pao" → cria tarefa no checklist
- "Jarvis, o que o patrao me pediu hoje?" → consulta memorias/eventos do Patrao Carlos
- "Jarvis, manda 'to a caminho' pro Maria" → dispara via Evolution

##### Fase posterior (NAO fazer agora)

- **Grupos** — alto volume polui Mem0 e aumenta risco de ban. Quando fizer: so processa msg que menciona o usuario (`@numero`) ou e resposta a uma msg dele
- **Audio de resposta** — depende ElevenLabs/TTS (Fase 5)
- **Pesquisar contatos no historico** — aba dedicada com timeline visual da conversa por contato (alem da memoria/eventos atuais)
- **Resumir grupo da familia** — workflow que roda 1x ao dia se Julio quiser
- **Responder cliente automaticamente** — fora de escopo (alto risco)

##### Ordem de implementacao Modo 1

1. Subir Evolution API no EasyPanel (Docker oficial + Postgres/Redis dedicados) — meio dia
2. Conectar numero, escanear QR, validar com mensagem de teste — 1h
3. Migration: 2 campos novos em `pessoas` — 30min
4. Modulo `whatsapp/` backend (client + service + router) — 1 dia
5. Integracao com `chat/service.py` (reusar pipeline) — meio dia
6. Frontend: campos em /pessoas + pagina /whatsapp de status — meio dia
7. Testar com 1 contato monitorado em producao — meio dia

**Total estimado: 2.5-3 dias**

##### Por que essa abordagem

- **Sem tabela nova de mensagens** — reusa `conversas`/`mensagens` com `metadados.tipo`
- **Sem tabela nova de contatos monitorados** — reusa `pessoas` com 2 colunas a mais
- **Pipeline NLP intocado** — parsers + Mem0 + eventos ja sabem processar texto livre
- **UI quase de graca** — Memorias e Eventos da pessoa aparecem nas paginas existentes
- **Risco controlado** — Modo 1 nunca envia mensagem, so observa

#### 4. Proatividade — Jarvis te procura sem voce pedir
- Alem do briefing fixo das 8h, Jarvis detecta eventos e avisa:
  - "Email urgente do seu chefe"
  - "Reuniao em 15min, voce esta em casa, tem 20min de transito"
  - "Voce disse que ia ligar pro Paulo hoje — nao ligou"
- Requer: cron de polling Gmail/Calendar + scoring de urgencia + Web Push
- Esforco: 3 dias
- Depende: Gmail MCP + Calendar MCP prontos

#### 5. Automacoes n8n invocaveis por voz
- Julio ja tem o NEXUS n8n rodando
- Expor workflows como "tools" do Jarvis via webhook
- "Jarvis, roda o fluxo de fechamento mensal"
- Multiplica poder sem escrever codigo novo
- Esforco: 1 dia

### Prioridade ALTA (impacto grande mas depende dos de cima)

#### 6. Contexto ambiente — localizacao + momento do dia
- Frontend ja e PWA, pega geolocalizacao
- "Voce esta no escritorio ha 9h, quer que eu bloqueie notificacoes nao-urgentes?"
- Mudanca de comportamento por contexto — notificacoes diferentes em casa vs escritorio vs viagem
- Esforco: 2 dias

#### 7. Voz em 2 vias (TTS + wake word)
- Hoje Julio grava audio e envia (Whisper funciona)
- Falta:
  - Resposta em audio (ElevenLabs ou OpenAI TTS) — ja no roadmap Fase 5
  - Wake word "Jarvis" (Porcupine ou OpenAI realtime)
- Transforma em assistente de verdade, maos livres
- Esforco: 4-5 dias

#### 8. Base de conhecimento pessoal + RAG expandido
- Ja tem modulo livros com RAG
- Expandir para:
  - Contratos PDF, notas fiscais, extratos bancarios
  - Notas do Obsidian/Notion
  - Fotos com OCR (GPT-4o Vision)
- "Quando foi a ultima revisao do carro?" -> busca nota fiscal automaticamente
- Esforco: 3-4 dias

### Prioridade MEDIA (requerem guardrails)

#### 9. Agente com autonomia para executar (nao so sugerir)
- Modelo: Jarvis sugere -> Julio aprova -> executa
- Ex: "Encontrei 3 emails que posso arquivar. Aprovar?"
- Requer:
  - Log de todas as acoes executadas
  - Rollback possivel
  - Guardrails (nunca deletar sem aprovar, nunca gastar dinheiro sem aprovar)
- Esforco: 5-7 dias (complexo, cuidado)

#### 10. Multi-modal — ver tela e responder sobre imagem
- GPT-4o ja suporta vision
- "Print dessa planilha — o que esta errado?"
- "Foto do extrato — classifica por categoria"
- Util para tarefas visuais rapidas
- Esforco: 2 dias

### Ranking por custo/beneficio imediato

| # | Feature | Esforco | Impacto |
|---|---------|---------|---------|
| 1 | Gmail MCP | 2 dias | 🔥🔥🔥🔥🔥 |
| 2 | Calendar MCP | 1 dia | 🔥🔥🔥🔥🔥 |
| 3 | WhatsApp | 3-4 dias | 🔥🔥🔥🔥🔥 |
| 4 | Proatividade | 3 dias | 🔥🔥🔥🔥🔥 |
| 5 | n8n invocavel | 1 dia | 🔥🔥🔥🔥 |
| 10 | Multi-modal | 2 dias | 🔥🔥🔥🔥 |
| 6 | Contexto ambiente | 2 dias | 🔥🔥🔥 |
| 8 | RAG expandido | 3-4 dias | 🔥🔥🔥 |
| 7 | Voz 2 vias | 4-5 dias | 🔥🔥🔥 |
| 9 | Agente autonomo | 5-7 dias | 🔥🔥🔥 (alto risco) |

### Ordem sugerida de implementacao
1. **Fase 4 (ja planejada):** Gmail + Calendar + Web Search
2. **Fase 4.5:** n8n invocavel (1 dia, multiplica valor do que ja existe)
3. **Fase 5:** WhatsApp (brasileiro precisa)
4. **Fase 6:** Proatividade (depende de Gmail + Calendar)
5. **Fase 7:** Voz 2 vias + wake word
6. **Fase 8:** RAG expandido (OCR + notas)
7. **Fase 9:** Multi-modal vision
8. **Fase 10:** Agente autonomo com guardrails

**Frameworks rejeitados:** LangChain, LangGraph (por enquanto). Motivo: overhead de abstracao dificulta debug, SDK direto + MCP e mais simples e mais rapido para 1 usuario. Reavaliar se o numero de tools passar de 20+ com fluxos condicionais complexos.

## Convencoes de Codigo
- **Python:** `snake_case` (funcoes/variaveis), `PascalCase` (classes/modelos), `SCREAMING_SNAKE_CASE` (constantes)
- **TypeScript:** `camelCase` (funcoes/variaveis), `PascalCase` (componentes/tipos)
- **Banco:** `snake_case` em portugues com prefixos obrigatorios (`id_`, `cod_`, `dat_`, `vlr_`, `qtd_`, `sts_`, `flg_`, `per_`)
- **Erros backend:** `{ "success": false, "error": "mensagem" }` — nunca expor stack trace em producao
- **Imports frontend:** absolutos via alias `@/`
- **Comentarios:** sempre em portugues
- **Timezone:** banco retorna UTC — sempre converter para `America/Sao_Paulo` (UTC-3) ao exibir
- **Rotas:** prefixo `/api` obrigatorio em TODAS as rotas do backend
- **Valores monetarios:** sempre `Numeric(10,2)` — nunca Float
- **Logs:** nunca logar senhas, tokens JWT, chaves API, CPF, dados de cartao

## Riscos Identificados

### ALTO
- **pgvector nao instalado no PostgreSQL** → primeira migracao DEVE executar `CREATE EXTENSION IF NOT EXISTS vector;`
- **Custo descontrolado de APIs IA** → dashboard de custos baseado em `tokens_entrada/saida` + `modelo_usado` na Fase 2
- **Claude API fora do ar** → fallback automatico para GPT-4o mini em erros 5xx/timeout
- **Acesso nao autorizado** → JWT obrigatorio + rate limiting agressivo em `/api/auth/login` (5 tent/min)
- **Chaves API vazadas nos logs** → Loguru com filter, nunca logar headers nem `.env`
- **APScheduler perde jobs em restart** → usar `SQLAlchemyJobStore` (jobs no banco)
- **Migracoes Alembic em producao** → sempre revisar arquivo gerado, testar local primeiro

### MEDIO
- Tabela `memorias` cresce rapido → indice HNSW desde o inicio
- Historico de mensagens sem limite → rotacao/arquivamento na Fase 3
- Rate limits Anthropic/OpenAI → httpx com retry exponencial (max 3) + circuit breaker
- Context window explode → truncar historico, usar resumo do Claude
- CORS permissivo → `CORS_ORIGINS` explicito, nunca `*`
- Redis sem persistencia → AOF ativado no EasyPanel
- Web Push revogado silenciosamente → tratar erro 410 Gone, marcar `flg_ativo=false`
- Monitoramento de sites bate em anti-bot → User-Agent realista + fallback manual
- Feature creep Fase 4/5 → roadmap rigido, so iniciar Fase 4 apos Fase 3 estavel

### BAIXO
- Mem0 instavel → memoria tambem no PostgreSQL, recuperavel
- SSE com muitas conexoes → async do FastAPI resolve para 1 usuario
- Embeddings sincronos → background task para pre-calcular
- EasyPanel fora do ar → backup semanal do banco + `.env`
- System prompt do Jarvis ruim → iterar ao longo do uso real

## Decisoes Tecnicas

| Decisao | Alternativas rejeitadas | Motivo |
|---|---|---|
| **Mem0 + pgvector + PostgreSQL** | So Mem0 / so pgvector | Mem0 auto-extrai fatos (economia de tokens), PostgreSQL garante recuperabilidade, pgvector para busca semantica direta quando necessario |
| **APScheduler em vez de Celery** | Celery + Redis broker | 1 usuario nao justifica broker separado. APScheduler roda dentro do mesmo processo FastAPI |
| **JWT simples, sem OAuth** | OAuth Google/GitHub | Projeto pessoal, 1 usuario. OAuth seria overhead sem beneficio |
| **Claude como cerebro principal** | Claude ou GPT exclusivo | Claude tem contexto mais longo e raciocinio melhor para memoria. GPT-4o mini fica para tarefas baratas e fallback |
| **Fallback automatico Claude→GPT** | Retry simples ou falha visivel | Jarvis e critico — nao pode parar se Claude cair |
| **PWA em vez de app nativo** | React Native / Flutter | Uma base de codigo funciona no celular e PC, PWA suporta push notifications, sem aprovacao de app store |
| **Dockerfile unico multi-stage** | docker-compose | Padrao do NEXUS + EasyPanel deploya mais facil com 1 container |
| **FastAPI + SSE (nao WebSocket)** | WebSocket para streaming | SSE e mais simples para streaming unidirecional (IA → usuario), reconecta automaticamente |
| **SQLAlchemy async + asyncpg** | psycopg3 sync | FastAPI e async-first, asyncpg e o driver mais rapido |
| **uv em vez de pip** | pip tradicional | uv e dramaticamente mais rapido (Rust), gerencia venv automaticamente |
| **Mem0 via PostgreSQL (nao Mem0 Cloud)** | Mem0 Cloud | Controle total dos dados, sem dependencia de servico externo adicional |
| **Tabelas Fase 3 criadas na Fase 1** | Criar so quando precisar | Evita migracoes complexas quando chegar na Fase 3 |
| **Embeddings OpenAI 1536 dim** | Embeddings 3072 dim (large) | text-embedding-3-small tem qualidade suficiente por muito menos custo |

## Planejamento — Resumo das Etapas
- **Etapa 1 (Entendimento):** Assistente pessoal estilo Jarvis do Homem de Ferro. 1 usuario (Julio). PWA multi-dispositivo. Referencias: ChatGPT Voice, Claude, Reclaim.ai, Zapier Agents, Lindy.ai
- **Etapa 2 (Stack):** Stack padrao 100% compativel. Unico gap: `vite-plugin-pwa` para habilitar PWA
- **Etapa 3 (Libs):** Backend — anthropic, openai, mem0ai, pgvector, apscheduler, pywebpush, elevenlabs, httpx, loguru, slowapi. Frontend — vite-plugin-pwa, zustand, tanstack-query, react-markdown. Rejeitadas: langchain (overhead), celery (overkill)
- **Etapa 4 (Modulos):** 7 modulos — auth, chat, memoria, ia (orquestrador interno), tarefas, notificacoes, config
- **Etapa 5 (Banco):** 8 tabelas. Destaques: pgvector (embedding 1536), JSONB para flexibilidade, tokens_entrada/saida para rastreabilidade de custo, soft delete universal, id_mem0 para sync com Mem0
- **Etapa 6 (Rotas):** 31 rotas totais. 20 na Fase 1, 2 na Fase 2, 9 na Fase 3
- **Etapa 7 (Pastas):** Estrutura modular padrao. Modulo `ia` sem router (chamado internamente). Modulo `tarefas` com `scheduler.py` + `jobs.py`
- **Etapa 8 (Dockerfile):** Multi-stage padrao. python:3.12-slim (nao alpine por causa do pgvector/asyncpg). Alembic upgrade automatico no startup
- **Etapa 9 (Envs):** Conjunto completo com variaveis obrigatorias (JWT, DB, IA) + opcionais (ElevenLabs, VAPID) para fases futuras
- **Etapa 10 (Roadmap):** 5 fases. Cada fase entrega Jarvis funcional. Fase 4 e 5 explicitamente "NO FUTURO"

## Problemas Conhecidos
- `email-validator` nao estava instalado — adicionado como dependencia (`pydantic[email]`)
- `TZ` env var conflitava com pydantic-settings — resolvido com `"extra": "ignore"` no model_config
- Migracao autogenerated nao importava pgvector — corrigido manualmente no arquivo de migracao
- pgvector precisou ser ativado manualmente na VPS via `CREATE EXTENSION IF NOT EXISTS vector`
- **passlib incompativel com bcrypt 5.x** — substituido por `bcrypt` direto (sem passlib). `hash_senha` e `verificar_senha` em `app/core/security.py` usam `bcrypt.hashpw`/`bcrypt.checkpw` diretamente
- **`cod_usuario` e `cod_pessoa` sem default no banco** — criadas sequencias PostgreSQL manualmente (`usuarios_cod_usuario_seq`, `pessoas_cod_pessoa_seq`). Modelos usam `server_default="nextval('...')"` para que SQLAlchemy omita essas colunas no INSERT
- **`server_default=func.now()` empata timestamps na mesma transacao** — usuario e assistente salvos no mesmo request do chat ficavam com `criado_em` identicos. Resolvido com desempate secundario `ORDER BY criado_em DESC, papel ASC` + `reversed()` em `listar_mensagens`

## Ultima Sessao
**2026-05-03** — **Migracao do cerebro do Jarvis para DeepSeek v4-pro** validada em producao. Contexto: o `ia/service.py` sempre usou GPT-4o para tudo (Claude API nunca foi integrada apesar do CLAUDE.md dizer o contrario). Processo: (1) Pesquisou API DeepSeek v4-pro/v4-flash. (2) Criou script de teste `backend/scripts/teste_parsers_deepseek.py` — 21 casos cobrindo os 4 parsers NLP. (3) v4-pro com thinking ativo retornava respostas vazias por conflito com `response_format: json_object` — corrigido com `extra_body={"thinking": {"type": "disabled"}}` nos parsers. (4) Resultado final: v4-pro 21/21 (100%) empate com GPT-4o nos parsers. (5) Implementacao: chat stream usa v4-pro com thinking ativo, parsers + titulo usam v4-pro sem thinking, Whisper e embeddings permanecem na OpenAI. (6) `DEEPSEEK_API_KEY` adicionada ao EasyPanel. Validado em producao — badge `deepseek-v4-pro` aparece na UI, Jarvis lembrou da reuniao ATS as 9:30 sem ser perguntado. Commit `6e006bb`.

**Gotcha descoberto:** DeepSeek v4-pro tem thinking ativo por padrao — incompativel com `response_format: {"type": "json_object"}` (retorna conteudo vazio). Solucao: `extra_body={"thinking": {"type": "disabled"}}` desativa o thinking para chamadas que precisam de JSON deterministico.

**2026-04-26** — Implementacao completa do **WhatsApp Modo 1 (Observador) via Evolution API v2.3** validada em producao. Entregas: (1) Modulo `app/modules/whatsapp/` com client HTTPX, webhook publico (validado por rede interna + nome da instancia, ja que Evolution v2.3 nao envia apikey no webhook global), pipeline NLP completo reaproveitando 4 parsers + Mem0 + eventos, score de urgencia normalizado sem acento, kill switch via `WHATSAPP_ENABLED`, dedup via Redis SETNX. (2) Migration: 2 campos novos em `pessoas` (`numero_whatsapp` unique + `flg_monitorar_whatsapp`). (3) Pagina `/whatsapp` com status, QR, contadores. (4) Integracao com a aba Pessoas em `MemoriaPage.tsx` — toggle de monitoramento. (5) Validacao em producao com NEXUS (558981504634): mensagem de gripe extraida como fato vinculado a pessoa, lembrete de consulta criado com data correta (27/04 14h BRT), push de urgencia disparou. Comprometeram **5 commits**: `b8437ba` (feat principal), `a7177f7` (debug log apikey), `c10bbe8` (fallback rede interna), `d8448e1` (fix data como list), `8a57203` (reescrita 3a pessoa pro Mem0), `928216d` (nome no titulo de lembrete/tarefa). Todos os 4 fixes registrados em `licoes.md`. Modo 2 (Comandante) e Fase WhatsApp 2.5 (migrar automacao n8n) registrados como roadmap futuro.

**2026-04-25** — 3 entregas: (1) Fix do parser de tarefa recorrente (commit `24ae41a` + push deploy EasyPanel). Bug: mensagem "Informo que a reuniao da diretoria mensal, realizada regularmente no primeiro sabado de cada mes, ocorrera no dia 02/05/2026" nao salvava lembrete. Causa raiz: o `TAREFA_RECORRENTE_PARSE_PROMPT` aceitava trechos como "todo primeiro sabado de cada mes" como recorrencia, mesmo quando a frase tambem informava UMA data unica especifica. Como `service.py:117` anula lembrete quando recorrente dispara, o lembrete nunca era salvo. Bonus: o cron gerado (`0 0 * * 6#1`) usa sintaxe `6#1` que o APScheduler nao suporta, falharia ao agendar de qualquer forma. Correcao: adicionados 4 exemplos negativos no prompt do recorrente + REGRA CRITICA explicita: "se menciona DATA ESPECIFICA UNICA (dd/mm/aaaa, amanha, sexta, dia 25), NAO e recorrente — e lembrete pontual". Validado via script de teste com a mensagem real. (2) MCP `jarvis-db` configurado em `c:/JARVIS/.mcp.json` (no `.gitignore` por conter senha) — agora consultas diretas ao PostgreSQL da VPS sem subir backend. (3) Teste comparativo de modelos para os 4 parsers NLP: `gpt-4o` (92% acerto, $310/ano) vs `gpt-4o-mini` (58%, $18/ano) vs `gpt-4.1-mini` (58%, $50/ano). Decisao: manter `gpt-4o` em tudo. Mini erra 33% no parser de tarefa por viesar positivo, gerando duplicacao de itens — economia de $290/ano nao compensa retrabalho. Revisitar na Fase 5 quando agentes autonomos aumentarem volume.

**2026-04-24** — Fix dos parsers NLP do chat. Bug: frases declarativas com horario especifico ("amanha tenho reuniao com X as 9:30") nao criavam lembrete nem evento — so extraiam fato via Mem0. Causa raiz: `LEMBRETE_PARSE_PROMPT` so tinha exemplos imperativos ("me lembra..."), e `EVENTO_PARSE_PROMPT` nao cobria reunioes futuras proximas. Correcoes: (1) novos exemplos declarativos com horario no prompt de lembrete, com REGRA explicita; (2) novos exemplos de reunioes futuras no prompt de evento; (3) lembrete e evento passaram a coexistir — removido `lembrete_info` da condicao de supressao em `chat/service.py`; (4) adicionado tratamento de `"amanha"` no switch `quando_raw` (bug colateral encontrado pela Vera: valores novos no prompt que o codigo nao tratava salvavam data errada). Commit `a571052` + push → deploy EasyPanel.

## Proximos Passos
1. **Monitorar latencia do DeepSeek v4-pro no chat** — thinking ativo pode adicionar delay antes do primeiro token. Se o usuario sentir lentidao, desativar thinking no stream com `extra_body={"thinking": {"type": "disabled"}}` em `_stream_deepseek`.
2. **Cadastrar contatos reais no WhatsApp Modo 1** — patrao, esposa, familia. Comecar com 2-3 e ampliar conforme uso.
2. **Avaliar acuracia da extracao Mem0 via WhatsApp** — apos 1 semana de uso real, conferir se memorias e eventos vinculados estao sendo precisos. Se houver muitos falsos positivos/negativos, ajustar prompts.
3. **WhatsApp Modo 2 (Comandante)** — adicionar deteccao de "Jarvis,..." no webhook (~1 dia). Permite Julio comandar pelo proprio zap.
4. **Fase WhatsApp 2.5 — Migrar automacao n8n** — substituir o workflow n8n diario por APScheduler + send_text. Desligar dependencia do n8n.
5. **Fase 4 (Integracoes externas)** — MCP Gmail, Google Calendar, Web Search.
6. **Testar audio no iOS** — verificar se `audio/mp4` funciona no Safari/iPhone.
7. **Upload PDF lento** — processamento sincrono pode travar em PDFs grandes; considerar background task.

## Ideias Futuras (Fase 5+)
- **Execucao autonoma no PC local** — permitir que o Jarvis execute tarefas no computador do usuario (abrir programa, responder email, extrair dado de site). 3 caminhos possiveis, do mais simples ao mais poderoso:
  1. **Agente Python local + fila no backend** — script rodando na bandeja do Windows, conectado via WebSocket, executa comandos via `subprocess`/`pyautogui`. Cobre 80% dos casos (abrir programa, rodar script, mover arquivo)
  2. **MCP local** — servidor MCP na maquina do usuario com ferramentas customizadas (filesystem, shell, apps). Requer ligar tool calling no Jarvis (hoje so retorna texto)
  3. **Computer Use da Anthropic** — Claude ve screenshot da tela e controla mouse/teclado. E o que o Clawbro (clawbro.ai) usa. Custo alto (cada screenshot e input de imagem), mas flexivel para qualquer tarefa visual
- **Diferencial do Jarvis vs Clawbro:** prompt personalizado, memoria Mem0 do contexto pessoal, eventos+pessoas+lembretes ja integrados, APScheduler para tarefas autonomas. Clawbro e generico; o Jarvis teria contexto completo do usuario.
- **Ordem recomendada:** comecar pelo caminho 1 quando chegar a fase, migrar para 2 ou 3 so se bater na limitacao real.

## Fase 5 — Agentes Autonomos (Roadmap)

**Objetivo:** transformar o Jarvis de "assistente reativo" (responde quando o usuario fala) em "plataforma de agentes autonomos" (agentes independentes rodando em background, com memoria dedicada e ferramentas especificas, reportando resultados ao usuario).

### Decisao de Modelos (atualizar arquitetura ao iniciar Fase 5)

Arquitetura hibrida — modelo certo para cada uso:

| Uso | Modelo | Por que |
|---|---|---|
| Chat principal (conversa com o Julio) | **Claude Sonnet 4.6/4.7** | Qualidade de conversa, coerencia em contexto longo, portugues natural, subtexto emocional. Custa ~3x GPT-4o mas vale para 1 usuario (R$ 30-80/mes diferenca) |
| Parsers NLP (detectar_lembrete, tarefa, evento) | **GPT-4o mini** | Response_format=json_object funciona bem, latencia baixa, custo baixo. Prompt curto e estruturado — Claude seria overkill |
| Cerebro dos agentes autonomos | **Claude Sonnet 4.x** | Tool calling em loop de multiplos passos e ponto fraco do GPT-4o (aluciana parametros, entra em loop). Claude e muito mais confiavel |
| Tarefas simples (titulo de conversa, classificacao) | **GPT-4o mini** | Barato e rapido |
| Transcricao de audio | **Whisper-1** | Ja funciona |
| Embeddings | **text-embedding-3-small** | Ja funciona |

**Atual:** Jarvis usa GPT-4o em tudo (chat, parsers, classificacao). Mudar para hibrido no inicio da Fase 5.

### Arquitetura do Modulo de Agentes

**Novo modulo `backend/app/modules/agentes/`:**
```
agentes/
├── models.py         # tabelas 'agentes' + 'execucoes_agente'
├── service.py        # registrar, agendar, executar agente
├── router.py         # /api/agentes/* (CRUD + disparar manual + listar execucoes)
├── base.py           # classe Agente (loop de execucao com tool calling)
└── tipos/            # implementacao de cada agente especializado
```

**2 tabelas novas:**
- `agentes` — id, cod_agente, nome, tipo, system_prompt (versionado), ferramentas[] (nomes das tools permitidas), cron (APScheduler), flg_ativo, criado_em
- `execucoes_agente` — id, id_agente, dat_inicio, dat_fim, sts_execucao (rodando/sucesso/falha), passos jsonb (log de cada tool call + resultado), resultado, tokens_consumidos

**3 camadas de memoria por agente:**
1. **Sistema** — prompt fixo (quem ele e, o que faz)
2. **Longo prazo** — Mem0 com namespace proprio (`agente_{id}`) para fatos e padroes que aprendeu
3. **Execucao** — log em `execucoes_agente.passos` (o que fez, o que deu certo/errado)

### Biblioteca de Ferramentas (tools expostas aos agentes)

Definidas no backend, cada agente recebe **so as que precisa** (principio do menor privilegio):
- `consultar_erp(loja, produto)` — via MCP `erp-db` ja existente
- `ler_gmail(filtros)` — via OAuth Gmail (Fase 4)
- `consultar_calendar(data)` — Google Calendar (Fase 4)
- `criar_lembrete(titulo, quando)` — modulo lembretes atual
- `buscar_memoria(query)` — Mem0 + pgvector
- `salvar_memoria(fato)` — Mem0
- `pesquisar_web(query)` — Brave Search ou similar
- `enviar_push(mensagem)` — Web Push atual
- `executar_sql_readonly(query)` — com permissoes restritas

### Pre-requisito Tecnico Critico: Tool Calling

Hoje o modulo `ia/service.py` chama Claude/GPT apenas com `messages.create(...)` retornando texto. Para agentes autonomos precisa ligar **tool calling** (API do Claude permite, esta so nao usado). Isso vai ser o primeiro PR da Fase 5.

### Ideias de Agentes (ainda NAO decidido qual sera o primeiro)

Opcoes possiveis, todas validas para o contexto do Julio (supervisor de logistica, 5 lojas):

- **Monitor de Estoque** — roda diario 7h, consulta ERP das 5 lojas, identifica rupturas/baixa cobertura, cria lembretes. Vantagem: MCP `erp-db` ja existe, resultado pratico imediato
- **Analise de Visitas** — roda sexta 18h, le eventos da semana, identifica lojas nao visitadas, gera relatorio. Usa tabela `eventos` ja criada na Fase D
- **Triagem de Email** — roda de hora em hora, le Gmail, classifica urgencias, notifica so o que importa. Requer Fase 4 (Gmail MCP) pronta
- **Briefing Matinal Inteligente** — evolucao do briefing atual, mas agora com raciocinio sobre eventos+pessoas+lembretes+estoque, prioriza e resume
- **Pesquisador sob Demanda** — usuario fala "pesquisa sobre X", agente busca web + memoria, resume, salva no Mem0, devolve resumo
- **Revisor de Decisoes** — roda semanal, le eventos de categoria `decisao`, avalia se ainda fazem sentido, sugere ajustes

**A definir com o Julio:** qual agente sera o primeiro (prova de conceito). Criterio: ter resultado pratico imediato, usar infra que ja existe, ser simples o suficiente para validar o modulo agentes antes de construir agentes mais complexos.

### Ordem de Implementacao

**Fase 5a — Fundacao (prova de conceito com 1 agente):**
1. Ligar tool calling no modulo `ia` (Claude + GPT suportam, so nao usado)
2. Criar modulo `agentes/` com modelos + base class + loop de execucao
3. Implementar **1 agente** como prova de conceito (a ser definido)
4. Validar: executa sozinho, loga passos, reporta resultado

**Fase 5b — Expansao (2-3 agentes reais):**
5. Mais agentes especializados
6. Dashboard no frontend: listar agentes, ver execucoes, ler logs, disparar manual
7. Self-reflection: agente avalia se teve sucesso, tenta de novo se nao deu

**Fase 5c — Orquestracao (futuro distante):**
8. Agente Planejador que cria outros agentes sob demanda
9. Agentes conversando entre si para resolver tarefa complexa (multi-agente)
10. Integracao com execucao no PC local (ver "Execucao autonoma" acima)

### Por que a base do Jarvis e ideal

~70% da infra de agentes autonomos ja esta pronta:
- Banco PostgreSQL + pgvector ✅
- Auth JWT ✅
- APScheduler com SQLAlchemyJobStore ✅
- Mem0 + embeddings ✅
- Chat + streaming SSE ✅
- Web Push ✅
- MCP do ERP ✅

**Falta principalmente:** tool calling + modulo agentes + ferramentas especificas. Comecar do zero (estilo Clawbro/AutoGPT genericos) seria reinventar toda essa infra sem ter o contexto pessoal do usuario.

### Framework para Fase 5 — Agno (decisao tomada em 2026-04-24)

**Usar Agno (https://docs.agno.com) APENAS no modulo `agentes/`** — nao migrar nada do que ja existe.

**Por que Agno na Fase 5:**
- Entrega pronto: loop de tool calling, memoria dedicada por agente, log de execucoes, Teams (multi-agentes)
- Em vez de ~3-4 dias construindo `base.py` + loop manual, cai para ~1-2 dias
- Roda SQLAlchemy 2.0 + PostgreSQL + pgvector por baixo — compativel com a stack atual
- APScheduler continua no controle do *quando*; Agno cuida do *como executar*

**O que NAO usar Agno:**
- Chat SSE streaming → manter SDK Anthropic direto
- Mem0 + pgvector → manter
- APScheduler + jobs → Agno nao substitui, manter
- Modulo livros (RAG) → manter pdfplumber atual
- Auth, config, checklist → nao tem relacao com IA

**Estrutura prevista do modulo agentes com Agno:**
```
backend/app/modules/agentes/
├── base.py       ← instancia Agent do Agno (sem construir loop do zero)
├── tipos/        ← monitor_estoque, triagem_email, etc.
├── router.py     ← /api/agentes/* (CRUD + disparar + listar execucoes)
└── service.py    ← agenda via APScheduler → chama agente Agno
```

**Instalacao:** `uv add agno` (Python 3.10+, suporta uv)

## Historico de Mudancas
| Data | Mudanca |
|------|---------|
| 2026-04-12 | Planejamento arquitetural completo (12 etapas) — Theo Python. CONTEXTO.MD e .claude/CLAUDE.md criados. Stack validada, modulos definidos, banco modelado, roadmap priorizado em 5 fases |
| 2026-04-12 | Fase 1 (Cerebro) 100% implementada — todos os modulos backend criados (auth, chat, memoria, ia), 9 tabelas no banco VPS, main.py com CORS+Loguru+rate limiting, Dockerfile multi-stage, /api/health respondendo OK |
| 2026-04-13 | Fase 2 (Interface) 100% implementada — frontend React completo: Vite+TypeScript+Tailwind+PWA, design system dark (zinc-950 + blue-500), LoginPage, ChatPage com SSE streaming, MemoriaPage, ConfigPage, Sidebar com lista de conversas, service worker gerado, build limpo 491KB |
| 2026-04-13 | Testes locais completos — 2 bugs corrigidos: passlib→bcrypt direto, sequences PostgreSQL para cod_usuario/cod_pessoa. Stack validada end-to-end: registro + login + chat SSE streaming funcionando |
| 2026-04-13 | Deploy inicial no EasyPanel — repositorio GitHub criado, auto-deploy configurado, VAPID keys geradas, Dockerfile CMD corrigido (|| ao inves de &&) |
| 2026-04-13 | Fase 3 parcial — Lembretes (tabela + APScheduler + CRUD + LembretesPage), Web Push VAPID (notificacoes funcionando no celular), deteccao de lembrete via chat (GPT-4o + json_object), Whisper-1 (transcricao de audio no chat) |
| 2026-04-13 | PWA instalavel — icones PNG validos (192x192 + 512x512), fix SPA catch-all para servir PNGs, fix includeAssets no VitePWA |
| 2026-04-13 | Layout responsivo mobile — sidebar drawer + overlay + bottom nav + botao menu no header do chat. Modelo fallback: GPT-4o-mini → GPT-4o |
| 2026-04-14 | Sistema de temas Arc Reactor/Homem de Ferro — CSS vars + data-theme + Zustand persist + pre-React em main.tsx. Bordas douradas amber-600 no tema Iron Man |
| 2026-04-14 | Modulo livros completo — upload PDF, pdfplumber, chunking por paragrafos, progresso, resumo IA, perguntas estudo, LivrosPage, integracao no chat. 3 novas tabelas: livros, livro_chunks, leitura_progresso |
| 2026-04-18 | Fase 3 concluida 100% — novo modulo tarefas recorrentes (/api/tarefas-agendadas) com CronTrigger timezone-aware, terceiro parser NLP detectar_tarefa_recorrente em paralelo (prioridade recorrente>lembrete>tarefa), aba "Recorrentes" em LembretesPage com cronParaTexto helper, reagendamento no startup |
| 2026-04-19 | Fase D (memoria episodica) completa — tabela eventos (dat_ocorreu, resumo, categoria, lojas, pessoas_envolvidas, embedding 1536), quarto parser NLP detectar_evento em paralelo com criterio amplo, marcador [EVENTO_REGISTRADO], backfill idempotente de historico (7 eventos criados), aba Eventos na MemoriaPage com filtros por categoria |
| 2026-04-19 | Fix ordem de mensagens no chat — server_default=func.now() empatava timestamps user+assistant na mesma transacao, virando ordem indeterministica. Desempate por `papel.asc()` na query DESC com `reversed()` no fim |
| 2026-04-24 | Fix parsers NLP — frases declarativas com horario ("amanha tenho reuniao as X") agora criam lembrete + evento. Lembrete e evento podem coexistir. Fix colateral: tratamento de "amanha" no switch quando_raw do service.py |
| 2026-04-25 | Fix parser de tarefa recorrente — frases que descrevem regularidade mas informam UMA data unica ("reuniao mensal, ocorrera em 02/05/2026") nao disparam mais como recorrente. Bug bloqueava criacao de lembrete porque service.py prioriza recorrente. Adicionados 4 exemplos negativos + REGRA CRITICA no `TAREFA_RECORRENTE_PARSE_PROMPT`. Commit `24ae41a` + push deploy EasyPanel |
| 2026-04-25 | MCP `jarvis-db` configurado em `.mcp.json` (gitignored) — consultas diretas ao PostgreSQL da VPS sem subir backend |
| 2026-04-25 | Decisao: manter `gpt-4o` em todos os 4 parsers NLP. Teste comparativo com 12 mensagens reais mostrou gpt-4o-mini com 58% de acerto (vs 92% do 4o), errando por viesar tarefa positiva — duplicacao de itens. Economia de $290/ano nao justifica retrabalho. Revisitar na Fase 5 |
