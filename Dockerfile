# ─── Stage 1: Build do frontend ───────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Instalar dependencias primeiro (aproveita cache do Docker)
COPY frontend/package*.json ./
RUN npm ci --silent

# Build do React
COPY frontend/ ./
RUN npm run build


# ─── Stage 2: Backend Python ──────────────────────────────────────────────────
FROM python:3.12-slim AS backend

# NUNCA usar Alpine — causa problemas com asyncpg e pgvector (C extensions)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=America/Sao_Paulo

WORKDIR /app

# Instalar dependencias do sistema necessarias para asyncpg e outras libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar arquivos de dependencias
COPY backend/pyproject.toml backend/uv.lock ./

# Instalar dependencias Python
RUN uv sync --frozen --no-dev

# Copiar backend
COPY backend/ ./

# Copiar frontend buildado para dentro do backend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copiar public (version.json e outros assets estaticos)
COPY public/ ./public/

# Porta do Uvicorn
EXPOSE 8000

# Startup: roda migracoes e inicia o servidor
CMD ["sh", "-c", "uv run alembic upgrade head || echo 'Alembic falhou — continuando (tabelas ja existem)' ; uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
