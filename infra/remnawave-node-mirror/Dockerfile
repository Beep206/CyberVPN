# syntax=docker/dockerfile:1.7

ARG REMNAWAVE_NODE_VERSION=3.4.1
ARG REMNAWAVE_NODE_COMMIT=44912631321664dbd5822e9bf8d96766ccff7c93
ARG REMNAWAVE_NODE_UPSTREAM_IMAGE=remnawave/node:3.4.1@sha256:0cdf386dd49f360fc885bb34bde21132e478e40f0deac62d616086ec0fa9257e

FROM node:24.20-trixie-slim@sha256:50c3b2f6988dfc307b86e5301d69611af31f4789bdf232863b07d3b02fe55ae0 AS verified-node-source

ARG REMNAWAVE_NODE_VERSION
ARG REMNAWAVE_NODE_COMMIT
WORKDIR /opt/remnawave-node
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth 1 --branch "${REMNAWAVE_NODE_VERSION}" \
        https://github.com/remnawave/node.git /opt/remnawave-node \
    && test "$(git rev-parse HEAD)" = "${REMNAWAVE_NODE_COMMIT}"
COPY verify-upstream-3.4.1.mjs /usr/local/share/cybervpn/remnawave-node/verify-upstream-3.4.1.mjs
RUN REMNAWAVE_NODE_SOURCE_ROOT=/opt/remnawave-node \
    node /usr/local/share/cybervpn/remnawave-node/verify-upstream-3.4.1.mjs

# CyberVPN mirrors the reviewed upstream multi-architecture image into its
# attested release namespace; no binary or runtime mutation is performed.
FROM ${REMNAWAVE_NODE_UPSTREAM_IMAGE}

ARG REMNAWAVE_NODE_VERSION
ARG REMNAWAVE_NODE_COMMIT

LABEL org.opencontainers.image.title="CyberVPN Remnawave node mirror"
LABEL org.opencontainers.image.version="${REMNAWAVE_NODE_VERSION}"
LABEL org.opencontainers.image.base.digest="sha256:0cdf386dd49f360fc885bb34bde21132e478e40f0deac62d616086ec0fa9257e"
LABEL org.opencontainers.image.revision="${REMNAWAVE_NODE_COMMIT}"

RUN --mount=from=verified-node-source,source=/tmp,target=/tmp/source-proof \
    test -s /tmp/source-proof/cybervpn-node-3.4.1-verified \
    && node -e 'const fs = require("node:fs"); const zod = require("/opt/app/dist/node_modules/zod/package.json"); const plugins = require("/opt/app/dist/node_modules/@remnawave/node-plugins/package.json"); const bundle = fs.readFileSync("/opt/app/dist/main.js", "utf8"); if (zod.version !== "4.5.4" || plugins.version !== "0.8.2" || !bundle.includes("zod/compile") || !bundle.includes("this.nodeVersion=\"3.4.1\"")) process.exit(1)'
