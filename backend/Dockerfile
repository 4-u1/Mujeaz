# Build context: repository root (needs backend/ and evals/data/).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/backend

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --upgrade pip && pip install -e .

COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY evals/data /srv/evals/data

RUN useradd --system --uid 10001 mujeaz && chown -R mujeaz /srv
USER mujeaz
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
