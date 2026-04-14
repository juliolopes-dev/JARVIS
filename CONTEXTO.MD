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
| GET | `/api/tarefas` | Listar tarefas agendadas (Fase 3) | ✅ |
| POST | `/api/tarefas` | Criar tarefa (Fase 3) | ✅ |
| PUT | `/api/tarefas/{id}` | Atualizar tarefa (Fase 3) | ✅ |
| DELETE | `/api/tarefas/{id}` | Remover tarefa (Fase 3) | ✅ |
| POST | `/api/tarefas/{id}/executar` | Executar manualmente (Fase 3) | ✅ |
| POST | `/api/notificacoes/subscrever` | Registrar push (Fase 3) | ✅ |
| DELETE | `/api/notificacoes/subscrever` | Remover push (Fase 3) | ✅ |
| POST | `/api/notificacoes/testar` | Teste push (Fase 3) | ✅ |
| GET | `/api/health` | Healthcheck | ❌ |
| GET | `/api/version` | Versao do backend | ❌ |

**Total: 31 rotas** | Fase 1: 20 | Fase 2: 2 | Fase 3: 9

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
│       │   └── ConfigPage.tsx
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useChat.ts
│       │   └── usePushNotification.ts
│       ├── services/
│       │   ├── api.ts
│       │   ├── authService.ts
│       │   ├── chatService.ts
│       │   └── memoriaService.ts
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
│   │   │   │   ├── scheduler.py
│   │   │   │   └── jobs.py
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
- [x] **Fase 3 parcial — Autonomia:** ✅ APScheduler com SQLAlchemyJobStore, ✅ Web Push VAPID (notificacoes no celular), ✅ Lembretes via chat (NLP) e manual (LembretesPage), ✅ Whisper-1 (audio→texto→envia), 🔲 Briefing diario, 🔲 Tarefas recorrentes por linguagem natural, 🔲 Gerenciamento de tarefas agendadas
- [ ] **Fase 4 — Integracoes (FUTURO):** MCP Gmail, MCP Google Calendar, MCP Web Search
- [ ] **Fase 5 — Voz (FUTURO):** ElevenLabs (voz), Claude Vision (imagens)

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

## Ultima Sessao
**2026-04-13** — Sessao intensa de features e bugfixes pos-deploy. Jarvis em producao no EasyPanel. Implementados: lembretes via chat (NLP→APScheduler) e manual (LembretesPage), Web Push VAPID (notificacoes chegam no celular), transcricao de audio via Whisper-1 (microfone no chat), PWA instalavel (icones corrigidos), layout responsivo mobile (sidebar drawer + bottom nav + botao menu). Modelo fallback trocado de GPT-4o-mini para GPT-4o. URL producao: https://applications-jarvis.tbs25p.easypanel.host

## Proximos Passos
1. **Fase 3 restante** — briefing diario (APScheduler job) + tarefas por linguagem natural + gerenciamento de tarefas agendadas
2. **Fase 4 (Integracoes FUTURO)** — MCP Gmail, Google Calendar, Web Search
3. **Testar audio no iOS** — verificar se `audio/mp4` funciona no Safari/iPhone

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
