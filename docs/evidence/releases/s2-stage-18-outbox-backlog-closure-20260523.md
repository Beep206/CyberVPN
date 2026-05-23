# S2-STAGE-18 Outbox Backlog Closure Evidence

**Stage:** `S2-STAGE-18: Post-Launch Stabilization And S3 Readiness`
**Date:** 2026-05-23
**Snapshot time:** 2026-05-23T11:31:12Z
**Runtime host:** `prod-app-1`
**Runtime release tag:** `stage2-public-rc.5`
**Decision:** `OUTBOX_BACKLOG_CLOSED_FOR_S2_WITH_ACCEPTED_NO_TRANSPORT`

---

## 1. Summary

The first S2 stabilization snapshot found 17 pending outbox events and 34 pending outbox publications.

These events were not customer-runtime payment/provisioning failures. They were stale growth/invite/entitlement events:

```text
growth_code.issued
growth_code.redeemed
invite.redeemed
entitlement.grant.activated
```

Production S2 currently has:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
No production NATS service in the app compose stack
```

Therefore the backlog was closed as a controlled S2 stabilization operation, not as a real NATS publication. The closure used the existing outbox repository lifecycle:

```text
claim -> submitted -> published
```

Each publication was marked with `publication_payload.status=accepted_no_transport` so future audits can distinguish this from real broker publication.

---

## 2. Safety Precondition

A fresh production backup was taken before the database mutation.

```text
started_at_utc=2026-05-23T11:29:13+00:00
backup_dir=/srv/cybervpn/backups/daily-20260523T112913Z
cybervpn_dump=/srv/cybervpn/backups/daily-20260523T112913Z/cybervpn-20260523T112913Z.dump
cybervpn_table_count=121
remnawave_dump=/srv/cybervpn/backups/daily-20260523T112913Z/remnawave-20260523T112913Z.dump
remnawave_table_count=36
finished_at_utc=2026-05-23T11:29:14+00:00
status=ok
```

---

## 3. Pre-Closure State

Observed before closure:

```text
partner_event_backbone_enabled=False
before_pending_events=17
before_pending_publications=34
before_pending_by_event={"invite.redeemed": 5, "growth_code.issued": 2, "growth_code.redeemed": 5, "entitlement.grant.activated": 5}
outbox_publications_total=34
outbox_publications_by_status={"pending": 34}
outbox_events_status_all={"pending_publication": 17}
outbox_publications_for_pending_events=34
```

The two configured publication consumers are:

```text
analytics_mart
operational_replay
```

---

## 4. Closure Operation

Lease owner:

```text
s2-stage18-outbox-closure-20260523
```

Operation result:

```text
claimed_per_consumer={'analytics_mart': 17, 'operational_replay': 17}
closed_publications=34
after_pending_events=0
after_published_events=17
after_pending_publications=0
after_published_publications=34
accepted_no_transport_publications=34
after_events_by_status={"published": 17}
after_publications_by_status={"published": 34}
status=ok
```

Post-closure audit split:

```text
accepted_no_transport_by_consumer={"analytics_mart": 17, "operational_replay": 17}
accepted_no_transport_by_event={"invite.redeemed": 10, "growth_code.issued": 4, "growth_code.redeemed": 10, "entitlement.grant.activated": 10}
```

Publication payload marker:

```text
status=accepted_no_transport
stage=S2-STAGE-18
closed_by=s2-stage18-outbox-closure-20260523
partner_event_backbone_enabled=false
```

---

## 5. Post-Closure Health Checks

Runtime services remained healthy:

```text
cybervpn-admin                running   healthy
cybervpn-backend              running   healthy
cybervpn-frontend             running   healthy
cybervpn-postgres             running   healthy
cybervpn-postgres-exporter    running   healthy
cybervpn-redis-exporter       running   healthy
cybervpn-remnawave            running   healthy
cybervpn-remnawave-postgres   running   healthy
cybervpn-remnawave-valkey     running   healthy
cybervpn-scheduler            running   healthy
cybervpn-telegram-bot         running   healthy
cybervpn-valkey               running   healthy
cybervpn-worker               running   healthy
```

Public probes:

```text
https://api.cyber-vpn.net/health             http=200
https://cyber-vpn.net/ru-RU                  http=200
https://cyber-vpn.net/ru-RU/miniapp/home     http=200
https://admin.cyber-vpn.net/ru-RU/login      http=200
```

HTTP/3/QUIC remained enabled:

```text
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

Observability:

```text
Alertmanager active_alerts=0
Prometheus Server is Ready.
```

Sampled logs after closure:

```text
No outbox/NATS/runtime exception was observed.
Two partner_auth.refresh_failed missing_token warnings were observed from unauthenticated refresh attempts; they are not related to the outbox closure and are not a P0/P1 launch blocker.
```

---

## 6. Decision And Follow-Up

```text
OUTBOX_BACKLOG_CLOSED_FOR_S2_WITH_ACCEPTED_NO_TRANSPORT
```

S2 stabilization backlog is closed. This does **not** approve S3 event-backbone readiness.

Before S3 Partner/Reseller Platform execution:

1. decide whether production S3 will run NATS/JetStream;
2. enable `PARTNER_EVENT_BACKBONE_ENABLED=true` only after NATS runtime evidence;
3. prove real dispatcher publication and consumer receipt flow;
4. add alerting for old pending outbox publications;
5. avoid treating `accepted_no_transport` records as proof of real broker delivery.

---

## 7. Documentation And Security Checks

Local checks before committing this evidence:

```text
git diff --check
result=pass
```

```text
grep secret/token/password patterns in changed S2 docs
result=no matches
```

```text
SECURITY_ARTIFACT_DIR=.tmp/s2-stage18-outbox-security-docs GITLEAKS_EXIT_CODE=1 bash scripts/security/scan-secrets.sh
result=no leaks found
scanned_bytes=159115602
```
