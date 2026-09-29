# syntax=docker/dockerfile:1.7

ARG REMNAWAVE_BACKEND_VERSION=3.4.4
ARG REMNAWAVE_BACKEND_COMMIT=b22970cc88481a7e278b5767721672a18f8b2ada
ARG REMNAWAVE_FRONTEND_COMMIT=cb4453bcfa4254ef91301f9a68d727da861487fb
ARG REMNAWAVE_BACKEND_UPSTREAM_IMAGE=remnawave/backend:3.4.4@sha256:63ef481550bbf49dabfa514c95d94109619cc85607730b308f7ad0b9b5599f06

FROM node:24.21-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe AS patched-backend-build

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
COPY verify-upstream-3.4.4-regressions.mjs /usr/local/share/cybervpn/remnawave-backend-compat/verify-upstream-3.4.4-regressions.mjs
COPY overlay/ /opt/remnawave-backend/

RUN XRAY_CONFIG_VALIDATOR_PATH=/opt/remnawave-backend/src/common/helpers/xray-config/xray-config.validator.ts \
        node /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs \
    && REMNAWAVE_BACKEND_SOURCE_ROOT=/opt/remnawave-backend \
        node /usr/local/share/cybervpn/remnawave-backend-compat/patch-node-ssh-scoped-broker.mjs \
    && git diff --check \
    && npm ci --prefer-offline --no-audit --no-fund \
    && REMNAWAVE_BACKEND_SOURCE_ROOT=/opt/remnawave-backend \
        node /usr/local/share/cybervpn/remnawave-backend-compat/verify-upstream-3.4.4-regressions.mjs \
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
LABEL org.opencontainers.image.description="Remnawave 3.4.4 backend rebuilt from pinned source with VLESS RAW Vision compatibility and CyberVPN-only scoped Node SSH"
LABEL org.opencontainers.image.version="3.4.4-raw-vision-flow.1"
LABEL org.opencontainers.image.base.name="remnawave/backend:3.4.4"
LABEL org.opencontainers.image.base.digest="sha256:63ef481550bbf49dabfa514c95d94109619cc85607730b308f7ad0b9b5599f06"
LABEL org.opencontainers.image.revision="${REMNAWAVE_BACKEND_COMMIT}"
LABEL net.cybervpn.remnawave.compat="raw-vision-per-client-flow-v1"
LABEL net.cybervpn.remnawave.frontend.revision="${REMNAWAVE_FRONTEND_COMMIT}"
LABEL net.cybervpn.remnawave.node-ssh-broker="scoped-one-time-native-disabled-v2"

COPY --from=patched-backend-build /opt/remnawave-backend/dist /opt/cybervpn-patched-dist
COPY patch-xray-config-validator.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-xray-config-validator.mjs
COPY patch-node-ssh-scoped-broker.mjs /usr/local/share/cybervpn/remnawave-backend-compat/patch-node-ssh-scoped-broker.mjs
COPY verify-upstream-3.4.4-regressions.mjs /usr/local/share/cybervpn/remnawave-backend-compat/verify-upstream-3.4.4-regressions.mjs
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
