# syntax=docker/dockerfile:1.7

ARG REMNAWAVE_BACKEND_VERSION=3.4.3
ARG REMNAWAVE_BACKEND_COMMIT=f8ad8ad3410252215ca7b2e429d157bd275ec564
ARG REMNAWAVE_FRONTEND_COMMIT=c2c9ba3b476e4914a3b17e8ce677ab9255e1c02f
ARG REMNAWAVE_BACKEND_UPSTREAM_IMAGE=remnawave/backend:3.4.3@sha256:4ea85b2fc16bd3e5d367b61afc07ec219133eaa12dd7b5e898adc33c84515422

FROM node:24.20-trixie-slim@sha256:50c3b2f6988dfc307b86e5301d69611af31f4789bdf232863b07d3b02fe55ae0 AS patched-backend-build

ARG REMNAWAVE_BACKEND_VERSION
ARG REMNAWAVE_BACKEND_COMMIT
ARG REMNAWAVE_FRONTEND_COMMIT

WORKDIR /opt/remnawave-backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth 1 --branch "${REMNAWAVE_BACKEND_VERSION}" \
        https://github.com/remnawave/backend.git /opt/remnawave-backend \
    && test "$(git rev-parse HEAD)" = "${REMNAWAVE_BACKEND_COMMIT}" \
    && test "$(node -p 'require("./package.json").version')" = "${REMNAWAVE_BACKEND_VERSION}"

COPY patch-xray-config-validator.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs
COPY patch-node-ssh-scoped-broker.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-node-ssh-scoped-broker.mjs
COPY verify-upstream-3.4.3-regressions.mjs /usr/local/share/cybervpn/remnawave-backend-compat/verify-upstream-3.4.3-regressions.mjs
COPY overlay/ /opt/remnawave-backend/

RUN XRAY_CONFIG_VALIDATOR_PATH=/opt/remnawave-backend/src/common/helpers/xray-config/xray-config.validator.ts \
        node /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs \
    && REMNAWAVE_BACKEND_SOURCE_ROOT=/opt/remnawave-backend \
        node /usr/local/share/cybervpn/remnawave-backend-compat/patch-node-ssh-scoped-broker.mjs \
    && git diff --check \
    && npm ci --prefer-offline --no-audit --no-fund \
    && REMNAWAVE_BACKEND_SOURCE_ROOT=/opt/remnawave-backend \
        node /usr/local/share/cybervpn/remnawave-backend-compat/verify-upstream-3.4.3-regressions.mjs \
    && npx --no-install oxfmt --check \
        src/common/config/app-config/config.schema.ts \
        src/common/helpers/xray-config/xray-config.validator.ts \
        src/modules/node-ssh/cybervpn-node-ssh-broker.controller.ts \
        src/modules/node-ssh/cybervpn-node-ssh-broker.credentials.ts \
        src/modules/node-ssh/cybervpn-node-ssh-broker.service.ts \
        src/modules/node-ssh/node-ssh.module.ts \
        src/modules/node-ssh/ssh/ssh-terminal.gateway.ts \
    && npm run lint \
    && npm run migrate:generate \
    && npm run build \
    && test -s dist/app.js \
    && test -s dist/processors.js \
    && test -s dist/scheduler.js

FROM ${REMNAWAVE_BACKEND_UPSTREAM_IMAGE}

ARG REMNAWAVE_BACKEND_VERSION
ARG REMNAWAVE_BACKEND_COMMIT
ARG REMNAWAVE_FRONTEND_COMMIT

LABEL org.opencontainers.image.title="CyberVPN Remnawave backend compatibility"
LABEL org.opencontainers.image.description="Remnawave 3.4.3 backend rebuilt from pinned source with VLESS RAW Vision compatibility and CyberVPN-only scoped Node SSH"
LABEL org.opencontainers.image.version="3.4.3-raw-vision-flow.2"
LABEL org.opencontainers.image.base.name="remnawave/backend:3.4.3"
LABEL org.opencontainers.image.base.digest="sha256:4ea85b2fc16bd3e5d367b61afc07ec219133eaa12dd7b5e898adc33c84515422"
LABEL org.opencontainers.image.revision="${REMNAWAVE_BACKEND_COMMIT}"
LABEL net.cybervpn.remnawave.compat="raw-vision-per-client-flow-v1"
LABEL net.cybervpn.remnawave.frontend.revision="${REMNAWAVE_FRONTEND_COMMIT}"
LABEL net.cybervpn.remnawave.node-ssh-broker="scoped-one-time-native-disabled-v2"

COPY --from=patched-backend-build /opt/remnawave-backend/dist /opt/cybervpn-patched-dist
COPY patch-xray-config-validator.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs
COPY patch-node-ssh-scoped-broker.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-node-ssh-scoped-broker.mjs
COPY verify-upstream-3.4.3-regressions.mjs /usr/local/share/cybervpn/remnawave-backend-compat/verify-upstream-3.4.3-regressions.mjs
COPY verify-openapi-nullability.mjs /usr/local/share/cybervpn/remnawave-backend-compat/verify-openapi-nullability.mjs

RUN node /usr/local/share/cybervpn/remnawave-backend-compat/verify-openapi-nullability.mjs /opt/app/openapi.json \
    && test "${__RW_METADATA_VERSION}" = "${REMNAWAVE_BACKEND_VERSION}" \
    && test "${__RW_METADATA_GIT_BACKEND_COMMIT}" = "${REMNAWAVE_BACKEND_COMMIT}" \
    && test "${__RW_METADATA_GIT_FRONTEND_COMMIT}" = "${REMNAWAVE_FRONTEND_COMMIT}" \
    && rm -rf /opt/app/dist \
    && mv /opt/cybervpn-patched-dist /opt/app/dist \
    && chmod +x /opt/app/dist/cli.js \
    && test -s /opt/app/dist/app.js \
    && test -s /opt/app/dist/processors.js \
    && test -s /opt/app/dist/scheduler.js
