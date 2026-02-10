# Stage 1: Builder — compiles C-extensions (argon2-cffi, asyncpg, etc.)
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./

# SEC: CVE-2026-1703 — Update pip to secure version
RUN pip install --no-cache-dir --upgrade "pip>=26.0"
RUN pip install --no-cache-dir .

# Stage 2: Runtime — lean image without build-essential
FROM python:3.13-slim

# SEC-002: Create non-root user for security
RUN groupadd -r cybervpn && useradd -r -g cybervpn cybervpn

WORKDIR /app

# Copy installed packages and executables from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=cybervpn:cybervpn . .

# SEC-002: Switch to non-root user
USER cybervpn

EXPOSE 8000
EXPOSE 9091

CMD ["python", "-m", "src.serve"]
