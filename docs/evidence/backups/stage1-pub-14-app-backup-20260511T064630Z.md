# STAGE1-PUB-14 App And Remnawave Backup Evidence

Date: 2026-05-11T06:46:30Z

Stage: `STAGE1-PUB-14`

Result: PASS.

Server: `10.10.10.34` / `cybervpn-h-ops`

Runtime tag: `stage1-beta-rc.2`

## Scope

This backup evidence covers the current no-cost Stage 1 runtime:

- CyberVPN application PostgreSQL database;
- Remnawave PostgreSQL database;
- no Valkey/Redis durable backup, because Valkey is not a Stage 1 source of truth.

The backup was created while the Stage 1 app stack stayed online.

## App DB Backup

Command type:

```text
pg_dump -Fc --no-owner --no-acl
```

Artifact:

| Field | Value |
|---|---|
| Path | `/srv/storage/backups/cybervpn-stage1/postgres/stage1-pub-14-cybervpn-20260511T064630Z.dump` |
| Owner/mode | `root:root` / `0600` |
| Size | `711901` bytes |
| SHA-256 | `d769a412664ef7396c3b5577328fdda877ab1a16340cbcbbd782c53fc73bb3fc` |

Source DB smoke:

| Check | Value |
|---|---:|
| Alembic version | `20260423_p27_partner_events` |
| Public table count | `120` |

## Remnawave DB Backup

Command type:

```text
pg_dump -Fc --no-owner --no-acl
```

Artifact:

| Field | Value |
|---|---|
| Path | `/srv/storage/backups/cybervpn-stage1/remnawave/stage1-pub-14-remnawave-20260511T064630Z.dump` |
| Owner/mode | `root:root` / `0600` |
| Size | `144481` bytes |
| SHA-256 | `b8c85e4369524f38cf4bee789e125575eea37c38734fde68d221d7bbeedea28e` |

Source DB smoke:

| Check | Value |
|---|---:|
| Public table count | `36` |
| Migration table count | `1` |

## Backup Storage

Backup files are stored off-root under:

```text
/srv/storage/backups/cybervpn-stage1/
```

Observed files:

```text
/srv/storage/backups/cybervpn-stage1/postgres/stage1-pub-14-cybervpn-20260511T064630Z.dump 711901 bytes 600 root:root
/srv/storage/backups/cybervpn-stage1/remnawave/stage1-pub-14-remnawave-20260511T064630Z.dump 144481 bytes 600 root:root
```

## Runtime Health After Backup

The backup did not stop the live app stack.

```text
cybervpn-admin                  running   healthy
cybervpn-backend                running   healthy
cybervpn-frontend               running   healthy
cybervpn-postgres               running   healthy
cybervpn-postgres-exporter      running   healthy
cybervpn-redis-exporter         running   healthy
cybervpn-remnawave              running   healthy
cybervpn-remnawave-node-local   running   healthy
cybervpn-remnawave-postgres     running   healthy
cybervpn-remnawave-valkey       running   healthy
cybervpn-scheduler              running   healthy
cybervpn-telegram-bot           running   healthy
cybervpn-valkey                 running   healthy
cybervpn-worker                 running   healthy
```

## Valkey Policy

Valkey/Redis remains non-durable for Stage 1:

- it is used for cache/queues/rate limits;
- payment/provisioning/customer source-of-truth state must be recoverable from PostgreSQL;
- no Valkey dump is required for this gate.

## Residual Risk

This proves the current local/no-cost Stage 1 data path. It does not remove the earlier accepted risk that the current data services are on the home server rather than managed/private PostgreSQL and Valkey.
