FROM rust:1.86-bookworm AS builder

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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /workspace/services/helix-node/target/release/helix-node /usr/local/bin/helix-node

EXPOSE 8091

CMD ["helix-node"]
