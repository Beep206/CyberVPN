# ── Build stage ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies (for hiredis, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies to a virtual environment for clean copy
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir .

# ── Runtime stage ────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Security: create non-root user
RUN groupadd -r botuser && \
    useradd -r -g botuser -d /app -s /sbin/nologin botuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy application source
COPY src/ ./src/
COPY healthcheck.py ./

# Switch to non-root user
USER botuser

# Expose metrics port
EXPOSE 9092

# Healthcheck: verify Redis connectivity
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD ["python", "healthcheck.py"]

# Run the bot
ENTRYPOINT ["python", "-m", "src.main"]
