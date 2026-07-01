FROM python:3.13.13-alpine AS builder

RUN apk add --no-cache build-base

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.13.13-alpine AS runtime

RUN addgroup -S vpnagent && adduser -S -G vpnagent -h /app -s /sbin/nologin vpnagent

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=vpnagent:vpnagent src/ ./src/
COPY --chown=vpnagent:vpnagent healthcheck.py ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD python healthcheck.py

USER vpnagent

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
