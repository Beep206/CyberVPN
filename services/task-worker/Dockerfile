# Stage 1: Builder — install dependencies
FROM python:3.13.13-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base

COPY pyproject.toml ./

# Install into /install prefix for clean copy
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime — minimal image
FROM python:3.13.13-alpine AS runtime

# Security: run the worker as a non-root user.
RUN addgroup -S workeruser && \
    adduser -S -G workeruser -h /app -s /sbin/nologin workeruser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=workeruser:workeruser src/ ./src/
COPY --chown=workeruser:workeruser healthcheck.py ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Healthcheck using Redis PING
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
  CMD python healthcheck.py

USER workeruser

# Default: run TaskIQ worker with 2 workers and filesystem discovery
CMD ["taskiq", "worker", "src.broker:broker", "--workers", "2", "--fs-discover"]
