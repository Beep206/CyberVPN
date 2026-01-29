# Stage 1: Builder — install dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install into /install prefix for clean copy
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime — minimal image
FROM python:3.13-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ ./src/
COPY healthcheck.py ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Healthcheck using Redis PING
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
  CMD python healthcheck.py

# Default: run TaskIQ worker with 2 workers and filesystem discovery
CMD ["taskiq", "worker", "src.broker:broker", "--workers", "2", "--fs-discover"]
