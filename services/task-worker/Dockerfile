# Stage 1: Builder — install dependencies
FROM python:3.13.14-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN python -m venv /opt/venv && \
    pip install --no-cache-dir --upgrade "pip>=26.0" uv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" && \
    uv export --frozen --no-dev --no-emit-project --no-hashes --format requirements.txt --output-file /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps --requirement /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps .

# Stage 2: Runtime — minimal image
FROM python:3.13.14-alpine AS runtime

# Security: run the worker as a non-root user.
RUN addgroup -S -g 10001 workeruser && \
    adduser -S -D -H -u 10001 -G workeruser -h /app -s /sbin/nologin workeruser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --chown=workeruser:workeruser src/ ./src/
COPY --chown=workeruser:workeruser healthcheck.py ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Healthcheck using Redis PING
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
  CMD python healthcheck.py

USER 10001:10001

# Default: run TaskIQ worker with 2 workers and filesystem discovery
CMD ["taskiq", "worker", "src.broker:broker", "--workers", "2", "--fs-discover"]
