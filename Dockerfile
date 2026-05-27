FROM python:3.12-slim-bookworm

ARG INSTALL_EMBEDDINGS=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

COPY requirements.txt .
COPY requirements-embeddings.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt && \
    if [ "$INSTALL_EMBEDDINGS" = "true" ]; then \
        pip install --no-cache-dir --retries 10 --timeout 120 -r requirements-embeddings.txt; \
    fi && \
    mkdir -p /app/word_base/word_audio /app/.cache/huggingface

COPY app ./app
COPY frontend_shared/src/i18n/messages.json ./frontend_shared/src/i18n/messages.json
COPY migrations ./migrations

CMD ["python", "-m", "app.api_main"]
