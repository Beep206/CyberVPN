FROM python:3.13.14-alpine AS builder

ARG XRAY_VERSION=26.6.27
ARG XRAY_SHA256=b3e5902d06d6282fe53cfa2fc426058b9aeaa429b2c812e20887cd47f26d08bf

RUN apk add --no-cache build-base ca-certificates curl unzip

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN python -m venv /opt/venv && \
    pip install --no-cache-dir --upgrade "pip>=26.0" uv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade "pip>=26.0" && \
    uv export --frozen --no-dev --no-emit-project --no-hashes --format requirements.txt --output-file /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps --requirement /tmp/requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir --no-deps .

RUN curl -fsSLo /tmp/xray.zip "https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-64.zip" && \
    echo "${XRAY_SHA256}  /tmp/xray.zip" | sha256sum -c - && \
    mkdir -p /opt/xray && \
    unzip -q /tmp/xray.zip -d /opt/xray && \
    chmod 0755 /opt/xray/xray && \
    rm -f /tmp/xray.zip

FROM python:3.13.14-alpine AS runtime

RUN apk add --no-cache ca-certificates && \
    addgroup -S -g 10001 vpnagent && adduser -S -u 10001 -G vpnagent -h /app -s /sbin/nologin vpnagent

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/xray/xray /usr/local/bin/xray
COPY --chown=vpnagent:vpnagent src/ ./src/
COPY --chown=vpnagent:vpnagent healthcheck.py ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VPN_TEST_AGENT_XRAY_BINARY=/usr/local/bin/xray

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python healthcheck.py

USER vpnagent

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
