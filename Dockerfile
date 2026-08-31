# ===== Etapa 1: builder (compila dependencias) =====
FROM python:3.13-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===== Etapa 2: runtime (imagen ligera) =====
FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY app/ ./app/
COPY db/ ./db/
COPY alembic.ini .

# Usuario no root + directorio de evidencias
RUN useradd -m appuser && mkdir -p /app/data/evidence && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Migra y arranca
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
