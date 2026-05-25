# S3-STAGE-02 Production Role Seed Reconciliation Evidence

**Stage:** `S3-STAGE-02: Partner Domain Model And Role Contract`
**Date:** 2026-05-24
**Decision:** `PRODUCTION_ROLE_SEED_RECONCILED`
**Runtime host:** `prod-app-1`

---

## 1. Summary

The production `partner_account_roles` seed was older than the frozen S3 backend role contract.

This was safe to fix immediately because production had:

```text
partner_accounts=0
partner_account_users=0
PARTNER_EVENT_BACKBONE_ENABLED=false
```

The reconciliation was completed before moving to `S3-STAGE-03`, so the issue is not carried as a hidden tail.

---

## 2. Safety Backup

A fresh PostgreSQL backup was captured before the production mutation:

```text
started_at_utc=2026-05-24T15:57:29+0000
backup_dir=/srv/cybervpn/backups/s3-stage02-role-seed-20260524T155729Z
cybervpn_dump=/srv/cybervpn/backups/s3-stage02-role-seed-20260524T155729Z/cybervpn-20260524T155729Z.dump
cybervpn_table_count=121
finished_at_utc=2026-05-24T15:57:30+0000
status=ok
```

---

## 3. Reconciliation Method

The mutation was performed through the backend repository method, not through ad hoc SQL:

```text
PartnerAccountRepository.ensure_builtin_roles()
```

This ensures production role rows match the current backend builtin role definitions.

---

## 4. Before

```text
analyst:4
finance:4
manager:6
owner:8
support_manager:2
technical_manager=missing
traffic_manager:4
partner_accounts=0
partner_account_users=0
```

Mismatched before:

```text
analyst
finance
manager
owner
support_manager
traffic_manager
```

Missing before:

```text
technical_manager
```

---

## 5. After

```text
analyst:5
finance:6
manager:10
owner:13
support_manager:3
technical_manager:5
traffic_manager:8
partner_accounts=0
partner_account_users=0
mismatched_after=[]
```

---

## 6. Post-Change Runtime Health

Public probes after reconciliation:

```text
https://api.cyber-vpn.net/health             http=200
https://cyber-vpn.net/ru-RU                  http=200
https://cyber-vpn.net/ru-RU/miniapp/home     http=200
https://admin.cyber-vpn.net/ru-RU/login      http=200
```

Container health after reconciliation:

```text
cybervpn-admin                running healthy
cybervpn-backend              running healthy
cybervpn-frontend             running healthy
cybervpn-postgres             running healthy
cybervpn-postgres-exporter    running healthy
cybervpn-redis-exporter       running healthy
cybervpn-remnawave            running healthy
cybervpn-remnawave-postgres   running healthy
cybervpn-remnawave-valkey     running healthy
cybervpn-scheduler            running healthy
cybervpn-telegram-bot         running healthy
cybervpn-valkey               running healthy
cybervpn-worker               running healthy
```

---

## 7. Decision

```text
PRODUCTION_ROLE_SEED_RECONCILED
```

The production role seed tail is closed for the current S3 role matrix.

If the builtin role contract changes later, repeat this operation with a fresh backup and evidence before enabling any production partner runtime.
