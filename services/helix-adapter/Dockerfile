FROM rust:1.96-bookworm AS builder

WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates wget \
    && groupadd --gid 10001 helix \
    && useradd --uid 10001 --gid helix --no-create-home --home /nonexistent --shell /usr/sbin/nologin helix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN chown helix:helix /app

COPY --from=builder /app/target/release/helix-adapter /usr/local/bin/helix-adapter

EXPOSE 8088

USER helix:helix

CMD ["helix-adapter"]
