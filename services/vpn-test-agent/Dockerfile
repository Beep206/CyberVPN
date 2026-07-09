FROM python:3.13.14-alpine AS builder

RUN apk add --no-cache build-base

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN python -m venv /opt/venv && \
    pip install --no-cache-dir --upgrade "pip>=26.0" uv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" && \
    uv export --frozen --no-dev --no-emit-project --no-hashes --format requirements.txt --output-file /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps --requirement /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps .

FROM python:3.13.14-alpine AS runtime

RUN addgroup -S vpnagent && adduser -S -G vpnagent -h /app -s /sbin/nologin vpnagent

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=vpnagent:vpnagent src/ ./src/
COPY --chown=vpnagent:vpnagent healthcheck.py ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python healthcheck.py

USER vpnagent

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
