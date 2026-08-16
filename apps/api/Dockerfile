FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user so the app (and any archive it extracts) runs unprivileged.
RUN groupadd -r dna && useradd -r -g dna -d /app dna

COPY apps/api/pyproject.toml ./
COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations

RUN pip install -e . && \
    chown -R dna:dna /app

# Fixtures mounted at runtime via compose (not baked into the image)
USER dna

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
