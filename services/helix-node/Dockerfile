FROM rust:1.96-bookworm AS builder

WORKDIR /workspace

COPY services/helix-node/Cargo.toml services/helix-node/Cargo.toml
COPY services/helix-node/Cargo.lock services/helix-node/Cargo.lock
COPY services/helix-node/src services/helix-node/src
COPY services/helix-node/tests services/helix-node/tests
COPY packages/helix-runtime packages/helix-runtime

WORKDIR /workspace/services/helix-node
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates wget \
    && groupadd --gid 10001 helix \
    && useradd --uid 10001 --gid helix --no-create-home --home /nonexistent --shell /usr/sbin/nologin helix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN chown helix:helix /app

COPY --from=builder /workspace/services/helix-node/target/release/helix-node /usr/local/bin/helix-node

EXPOSE 8091

USER helix:helix

CMD ["helix-node"]
