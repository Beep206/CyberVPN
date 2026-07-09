# Stage 1: Builder — compiles C-extensions (argon2-cffi, asyncpg, etc.)
FROM python:3.13.14-alpine AS builder

RUN apk add --no-cache build-base

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# SEC: CVE-2026-1703 — Update pip to secure version
RUN python -m venv /opt/venv && \
    pip install --no-cache-dir --upgrade "pip>=26.0" uv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" && \
    uv export --frozen --no-dev --no-emit-project --no-hashes --format requirements.txt --output-file /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps --requirement /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps .

# Stage 2: Runtime — lean image without build-essential
FROM python:3.13.14-alpine

# SEC-002: Create non-root user for security. Keep the UID/GID aligned with Helm.
RUN addgroup -S -g 10001 cybervpn && \
    adduser -S -D -H -u 10001 -G cybervpn cybervpn

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --chown=cybervpn:cybervpn . .

# SEC-002: Switch to non-root user
USER 10001:10001

EXPOSE 8000
EXPOSE 9091

CMD ["python", "-m", "src.serve"]
