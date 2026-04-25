# Jarvis — Regras Especificas do Projeto

> Regras que valem APENAS para o Jarvis. As regras globais do NEXUS (em `C:/Users/julio/.claude/CLAUDE.md`) continuam valendo.

## Sobre o Projeto
Assistente pessoal de IA (estilo Jarvis do Homem de Ferro) — 1 usuario, multi-dispositivo via PWA. Cerebro Claude + fallback GPT-4o, memoria persistente Mem0 + pgvector, tarefas autonomas APScheduler, notificacoes Web Push, transcricao de audio via Whisper. Backend FastAPI, frontend React+Vite PWA.

## Banco de Dados
- **Localizacao:** VPS — EasyPanel (nunca local em producao)
- **Engine:** PostgreSQL com extensao `pgvector` obrigatoria
- **ORM:** SQLAlchemy 2.0 async — estilo declarativo com `Mapped` / `mapped_column`
- **Driver:** `asyncpg` — `postgresql+asyncpg://...`
- **Migracoes:** Alembic — nunca alterar banco manualmente em producao
- **Primeira migracao OBRIGATORIAMENTE executa:** `CREATE EXTENSION IF NOT EXISTS vector;` antes de criar tabelas
- **Indice HNSW em `memorias.embedding`** criado manualmente na migracao: `CREATE INDEX ON memorias USING hnsw (embedding vector_cosine_ops);`
- **Convencoes:** snake_case em portugues com prefixos obrigatorios (`id_`, `cod_`, `dat_`, `vlr_`, `qtd_`, `sts_`, `flg_`, `per_`)
- **Timezone:** banco retorna UTC — sempre converter para `America/Sao_Paulo` (UTC-3) ao exibir
- **Embeddings:** dimensao fixa `1536` (OpenAI `text-embedding-3-small`)

## Stack
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Alembic + PostgreSQL + pgvector + Redis
- **Frontend:** React + Vite + TypeScript + Tailwind + PWA (`vite-plugin-pwa`)
- **Auth:** JWT via `python-jose + passlib` — access token 10h, refresh token 30 dias. Usuario unico, sem OAuth social
- **IA:** Claude API (cerebro principal) + GPT-4o (tarefas simples + fallback automatico) + Whisper-1 (transcricao de audio) + Embeddings OpenAI text-embedding-3-small + Mem0 (auto-extracao de fatos)
- **Tarefas agendadas:** APScheduler com `SQLAlchemyJobStore` (jobs persistidos no PostgreSQL) — nunca usar JobStore em memoria
- **Notificacoes:** Web Push Notifications via `pywebpush` + VAPID keys
- **Logs:** Loguru com filter anti-leak (nunca loga headers, `.env`, chaves API, tokens JWT, senhas)
- **Gerenciador:** `uv` (nao pip) — comandos sempre `uv run ...`
- **Linter:** Ruff (substitui Black, Flake8, isort)
- **Libs principais backend:** anthropic, openai, mem0ai, pgvector, httpx, apscheduler, pywebpush, slowapi, loguru, asyncpg, redis, pydantic-settings, pdfplumber
- **Libs principais frontend:** axios, zustand, @tanstack/react-query, lucide-react, date-fns, sonner, vite-plugin-pwa, react-markdown

## MCPs disponiveis para este projeto
- **mem0** — gerenciador de memoria do Jarvis (auto-extracao de fatos)
- **easypanel** — deploy e gerenciamento de servicos na VPS
- **Fase 4 (FUTURO):** Gmail MCP, Google Calendar MCP, Web Search MCP

## Gotchas Conhecidos
- Banco retorna UTC — sempre converter para America/Sao_Paulo (UTC-3) ao exibir. FastAPI retorna datetime em ISO 8601, frontend formata com `date-fns`
- Toda rota do backend usa prefixo `/api` — NUNCA omitir. Backend serve frontend na mesma porta em producao
- Frontend usa `axios.create({ baseURL: '/api' })` — nunca hardcodar URL completa
- `python:3.12-slim` no Dockerfile (NUNCA Alpine) — Alpine causa problemas com C extensions do `asyncpg` e `pgvector`
- APScheduler DEVE usar `SQLAlchemyJobStore` — JobStore em memoria perde jobs em restart do container
- Claude API pode cair — SEMPRE ter fallback automatico para GPT-4o mini em erros 5xx/timeout no modulo `ia`
- Rate limiting OBRIGATORIO em `/api/auth/login` (max 5 tentativas/min via slowapi) — o Jarvis tem memoria pessoal critica
- Redis precisa estar com AOF ativado no EasyPanel — senao perde contexto de conversa em restart
- Web Push pode retornar erro 410 Gone (subscricao revogada pelo navegador) — marcar `flg_ativo=false` sem reenviar
- Mem0 e sincronizado com PostgreSQL via `id_mem0` — ao deletar memoria, remover dos dois lados
- `tokens_entrada`/`tokens_saida` SEMPRE preenchidos na tabela `mensagens` — rastreabilidade de custo e obrigatoria
- Embeddings OpenAI: usar `text-embedding-3-small` (1536 dim) — NAO usar o `large` (3072 dim) por custo
- **Arquivos estaticos da raiz (PNG, sw.js, manifest) sao interceptados pelo SPA catch-all** — adicionar EXPLICITAMENTE na lista `_static_root_files` em `main.py` antes do `@app.get("/{full_path:path}")`. Sem isso, `/pwa-192x192.png` retorna `text/html` e Chrome rejeita o PWA
- **VitePWA com `injectManifest` NAO copia PNGs automaticamente** — adicionar `pwa-192x192.png` e `pwa-512x512.png` no `includeAssets` do `vite.config.ts`. Sem isso os icones nao vao para o `dist`
- **Layout mobile responsivo** — sidebar usa drawer fixo (`fixed inset-y-0 left-0 z-40`) no mobile e `md:flex flex-shrink-0` no desktop. Controle separado no AppLayout com dois wrappers distintos. Sidebar interna tem `width` fixo sempre — quem controla visibilidade e o wrapper
- **Whisper-1** integrado em `app/modules/ia/service.py` → `POST /api/chat/transcrever` (multipart/form-data). Frontend usa `MediaRecorder` com `audio/webm;codecs=opus` (Chrome) ou `audio/mp4` (Safari)
- **SQLAlchemy async: `db.refresh()` NAO carrega relacionamentos** — apos `await db.commit()`, usar `select(...).options(selectinload(Model.rel))` em query nova. `refresh()` recarrega colunas escalares mas NAO lazy relationships. Sem isso: `MissingGreenlet: greenlet_spawn has not been called` ao serializar o relacionamento
- **Alembic autogenerate detecta tabelas externas como "to be dropped"** — tabelas como `mem0migrations`, `apscheduler_jobs`, `jarvis_memories` aparecem no diff como `op.drop_table(...)`. Sempre revisar e remover manualmente esses drops antes de aplicar a migracao. Nunca aplicar migracao autogenerate sem revisao manual
- **Modulo livros** — `app/modules/livros/` com `models.py` (Livro, LivroChunk, LeituraProgresso), `service.py`, `router.py`, `schemas.py`. Upload via multipart/form-data (max 50MB), processamento com `pdfplumber`, chunking por paragrafos com deteccao de capitulo
- **Modulo tarefas (recorrentes)** — `app/modules/tarefas/` usa a tabela `tarefas_agendadas` ja criada na migracao inicial (Fase 1). Rota `/api/tarefas-agendadas/*` (NAO `/api/tarefas`, que conflitaria com `/api/checklist/tarefas`). Usa `APScheduler CronTrigger.from_crontab(cron, timezone="America/Sao_Paulo")` — NUNCA omitir o timezone, senao os jobs disparam em UTC. Startup em `main.py` reagenda todas as tarefas com `sts_tarefa='ativa'` via `reagendar_todas()`
- **3 parsers de NLP rodam em paralelo no chat/service.py** — `detectar_lembrete` (pontual), `detectar_tarefa` (checklist), `detectar_tarefa_recorrente` (cron). Ordem de prioridade: recorrente > lembrete > tarefa. Se recorrente detectado, zerar `lembrete_info` para evitar duplicacao (o parser de lembrete pontual ocasionalmente aceita frases recorrentes). Cada parser tem seu prompt dedicado em `ia/prompts.py` com exemplos explicitos do que NAO e aquela categoria
- **Marcadores sinteticos enviados ao sistema prompt** — `[LEMBRETE_CRIADO: ...]`, `[TAREFA_CRIADA: ...]`, `[TAREFA_RECORRENTE_CRIADA: descricao | cron=X]` injetados no conteudo da IA para que a resposta confirme naturalmente. O prompt do sistema ensina o Jarvis a reagir a cada marcador — NUNCA dizer que houve erro a menos que o sistema retorne explicitamente um erro
- **`server_default=func.now()` retorna timestamp da transacao, nao do INSERT** — quando usuario e assistente sao salvos na mesma transacao/request (chat/service.py), ficam com `criado_em` identicos e a ordem vira indeterministica. Em `listar_mensagens` usar `ORDER BY criado_em DESC, papel ASC` + `reversed()` no fim, para que `user` apareca antes de `assistant` quando o timestamp empata. Vale para qualquer tabela com multiplos INSERTs por transacao (logs, auditoria)
- **Novos valores de `quando` em EVENTO_PARSE_PROMPT exigem tratamento no service.py** — o switch `quando_raw` em `chat/service.py` trata apenas `"hoje"`, `"ontem"` e `"amanha"` + fallback ISO. Ao adicionar exemplos novos no prompt com valores como `"amanha"` ou dia da semana (`"sexta"`), verificar se o switch ja cobre o novo valor. Strings nao tratadas caem no `fromisoformat()`, que falha silenciosamente e salva a data como hoje (errado). Dias da semana devem retornar ISO no prompt — o switch nao tem logica de calendario.

## Rotas
- **Prefixo obrigatorio:** `/api` — em TODAS as rotas
- **Base URL frontend:** `axios.create({ baseURL: '/api' })`
- **Streaming de resposta IA:** Server-Sent Events (SSE) via `StreamingResponse` do FastAPI
- **Healthcheck:** `GET /api/health` (sem auth) — EasyPanel usa para verificar saude
- **Version:** `GET /api/version` + `public/version.json` para cache busting

## Seguranca
- CORS: `CORS_ORIGINS` explicito — NUNCA `*` em producao
- Rate limiting obrigatorio em rotas de auth e publicas
- JWT em TODAS as rotas `/api/*` exceto `auth/login`, `auth/registrar`, `auth/refresh`, `health`, `version`
- `.env` NUNCA commitado — so `.env.example`
- Chaves API e `JWT_SECRET` sempre em variaveis de ambiente, nunca hardcoded
- Loguru com filter para nunca logar headers de request nem dados sensiveis
- Logar login: IP + email + resultado — NUNCA a senha
- Erros em producao: `{ "success": false, "error": "mensagem" }` — sem stack trace
- Custo de API: monitorar `tokens_entrada + tokens_saida` via dashboard (Fase 2) para evitar surpresas na fatura

## Deploy
- **Plataforma:** EasyPanel na VPS
- **Fluxo:** push GitHub → auto deploy via EasyPanel
- **Dockerfile:** unico na raiz — multi-stage (Node builder + Python 3.12-slim final)
- **Migracoes:** rodam automaticamente no startup via `alembic upgrade head`
- **Porta:** 8000 (padrao Uvicorn)
- **Timezone:** `ENV TZ=America/Sao_Paulo` no Dockerfile
- **Servicos necessarios na VPS:**
  - PostgreSQL com extensao `pgvector` instalada
  - Redis com AOF persistente ativado

## Versionamento e Cache (Frontend)
- `public/version.json` com campos `version` e `timestamp` — gerado no build
- Frontend checa `/version.json` a cada 5-10 minutos
- Se versao do servidor diferir da local: exibir Toast convidando a recarregar
- `index.html` servido com `Cache-Control: no-cache`

## Comandos do Projeto
```bash
# Dev frontend
cd frontend && npm run dev

# Dev backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Nova migracao
cd backend && uv run alembic revision --autogenerate -m "descricao"

# Aplicar migracao
cd backend && uv run alembic upgrade head

# Reverter migracao
cd backend && uv run alembic downgrade -1

# Build Docker local
docker build -t jarvis .

# Gerar VAPID keys (Fase 3)
npx web-push generate-vapid-keys
```

## Frontend (React + Vite)
- **tsconfig:** `noUnusedLocals` e `noUnusedParameters` devem ser `false` — o TypeScript strict padrao bloqueia builds por variaveis de hook ou parametros de callback que nao sao usados (ex: parametros de rotas, refs em closures)
- **SSE streaming:** usar `fetch` nativo com `Authorization` header — NUNCA `EventSource` (nao suporta headers customizados, logo nao da para passar JWT)
- **Proxy de dev:** `vite.config.ts` com `server.proxy['/api']` apontando para `localhost:8000` — sem hardcodar URL no frontend
- **PWA:** `vite-plugin-pwa` com `registerType: 'autoUpdate'` + `workbox.runtimeCaching` excluindo `/api/auth` de cache
- **Design system:** documentado em `.design-engineer/system.md` — zinc-950 base, blue-500 accent, Inter+JetBrains Mono, borders-only (sem sombras)

## Convencoes de Codigo
- **Python:** `snake_case` (funcoes/variaveis), `PascalCase` (classes/modelos), `SCREAMING_SNAKE_CASE` (constantes)
- **TypeScript:** `camelCase` (funcoes/variaveis), `PascalCase` (componentes/tipos)
- **Banco:** `snake_case` portugues com prefixos obrigatorios
- **Comentarios:** sempre em portugues
- **Imports frontend:** absolutos via alias `@/`
- **Estrutura modular:** um dominio = um modulo em `app/modules/`. Cada modulo tem `router.py`, `service.py`, `models.py`, `schemas.py`
- **Logica de negocio:** NUNCA nas rotas. Rotas so validam entrada e chamam o service
- **Respostas de erro backend:** `{ "success": false, "error": "mensagem" }` sempre
- **Exception handler global:** no `main.py` para capturar todo erro nao tratado e retornar no formato padrao sem stack trace em producao

## Regras Especificas do Jarvis
- **Fallback de IA obrigatorio** — qualquer chamada ao Claude que falhe (5xx/timeout) deve tentar automaticamente GPT-4o no modulo `ia`
- **Roteamento de modelos** — tarefas complexas (analise, raciocinio, memoria) vao para Claude; tarefas simples (titulo de conversa, classificacao, deteccao de lembrete) vao para GPT-4o
- **Transcricao de audio** — `POST /api/chat/transcrever` (multipart/form-data, campo `audio`). Limite 25MB. Retorna `{ "texto": "..." }`. Frontend: `MediaRecorder` segura→grava, solta→transcreve→envia direto
- **Memoria automatica** — toda mensagem do usuario passa pelo Mem0 para extracao automatica de fatos
- **Nunca deletar memorias fisicamente** — sempre soft delete (`flg_ativo=false`). Memoria pessoal e dado critico
- **System prompt do Jarvis** — fica em `app/modules/ia/prompts.py`, versionado no git. Iterar conforme uso real
- **Briefing diario** (Fase 3) — job APScheduler que roda no horario configurado em `configuracoes.horario_briefing` e dispara Web Push
- **Tarefas por linguagem natural** (Fase 3) — "todo dia as 8h me manda X" → Claude parseia → cria job APScheduler com cron expression
- **Modulo livros** — upload PDF, processamento `pdfplumber`, chunking inteligente (paragrafos + deteccao de capitulo), progresso por chunk, resumo ao fim de capitulo (GPT-4o), perguntas de fixacao (modo estudo), memoria automatica ao concluir livro (Mem0). Deteccao de "proximo trecho" no chat service para entrega inline
- **PDF upload** — `POST /api/livros/` via multipart/form-data. Limite 50MB configurado no router. Processamento sincrono no request (pode ser lento para PDFs grandes — considerar background task em versao futura)

## Atualizacao Automatica
Atualizar este `.claude/CLAUDE.md` sempre que:
- Um gotcha novo for descoberto durante a implementacao
- Uma decisao tecnica especifica for tomada que impacte futuras sessoes
- Um problema conhecido for resolvido de forma nao obvia
- Uma nova biblioteca for adicionada
- Uma convencao nova for estabelecida
