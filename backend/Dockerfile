FROM python:3.13-slim

# SEC-002: Create non-root user for security
RUN groupadd -r cybervpn && useradd -r -g cybervpn cybervpn

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=cybervpn:cybervpn pyproject.toml ./

# SEC: CVE-2026-1703 - Update pip to secure version
RUN pip install --no-cache-dir --upgrade "pip>=26.0"

RUN pip install --no-cache-dir -e .

COPY --chown=cybervpn:cybervpn . .

# SEC-002: Switch to non-root user
USER cybervpn

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
