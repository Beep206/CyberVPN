# Stage 2 Release Rehearsal Runbook

**Scope:** CyberVPN S2 Public Release 1.0
**Stage:** `S2-STAGE-15`
**Primary owner:** `@Sasha_Beep`
**Last verified:** 2026-05-23

---

## 1. Safety Rules

1. Do not expand public traffic during rehearsal.
2. Do not enable payment, trial, referral, promo, gift or autoprolongation kill switches during rehearsal unless the owner explicitly approves that action.
3. Do not run real payment/refund actions from an automation script.
4. Do not paste secrets, raw VPN configs, raw subscription URLs, bearer tokens, payment payloads or Telegram init data into evidence.
5. Never deploy a floating `main` as a production release identity.
6. Never disable HTTP/3/QUIC as part of rehearsal.
7. Keep `.org` as VPN node/subscription delivery only.
8. Keep the VPN node node-only.

---

## 2. Pre-Rehearsal Checks

Confirm repository state:

```bash
git status --short
git rev-parse HEAD
git tag --list 'stage2-public-rc.*' --sort=creatordate
```

Confirm remotes:

```bash
git ls-remote origin refs/heads/main 'refs/tags/stage2-public-rc.*'
git ls-remote github refs/heads/main 'refs/tags/stage2-public-rc.*'
```

Expected:

- GitLab `main` and GitHub `main` are synchronized before tagging;
- no unexpected dirty tracked files;
- unrelated local evidence files are not included.

---

## 3. Create RC Tag

After the S2-STAGE-15 evidence commit is created:

```bash
git tag -a stage2-public-rc.1 -m "Stage 2 public release candidate 1"
git push origin stage2-public-rc.1
git push github stage2-public-rc.1
```

GitLab must be pushed first.

If the tag already exists, do not force-update it without an explicit owner decision. Create `stage2-public-rc.2` instead.

---

## 4. Deploy Dry-Run

Run a no-network deploy rehearsal before any real deploy:

```bash
rm -rf .tmp/s2-stage15-dry-run
STAGE1_DEPLOY_DRY_RUN=true \
STAGE1_DEPLOY_EVIDENCE_DIR=.tmp/s2-stage15-dry-run \
STAGE1_RELEASE_TAG=stage2-public-rc.1 \
bash scripts/deploy/stage1-gitlab-deploy.sh all
```

Expected:

```text
No SSH, rsync, Docker build, compose restart or public smoke was executed.
```

This proves the deploy contract without touching production.

---

## 5. Public Route Probes

Run:

```bash
for url in \
  https://cyber-vpn.net/ru-RU \
  https://cyber-vpn.net/ru-RU/pricing \
  https://cyber-vpn.net/ru-RU/login \
  https://cyber-vpn.net/ru-RU/miniapp/home \
  https://admin.cyber-vpn.net/ru-RU/login \
  https://api.cyber-vpn.net/health \
  https://api.cyber-vpn.net/docs \
  https://cyber-vpn.org/ \
  https://cyber-vpn.org/api/sub/stage2-rehearsal-redacted; do
  curl -k -sS -o /tmp/cybervpn_probe_body \
    -w "$url http=%{http_code} redirect=%{redirect_url} time=%{time_total}\n" \
    --max-time 20 "$url"
done
```

Expected:

| Route | Expected |
|---|---|
| `cyber-vpn.net/ru-RU` | `200` |
| `cyber-vpn.net/ru-RU/pricing` | `200` |
| `cyber-vpn.net/ru-RU/login` | `200` |
| `cyber-vpn.net/ru-RU/miniapp/home` | `200` |
| `admin.cyber-vpn.net/ru-RU/login` | `200` |
| `api.cyber-vpn.net/health` | `200`, JSON `{"status":"ok"}` |
| `api.cyber-vpn.net/docs` | `404` |
| `cyber-vpn.org/` | redirect to `https://cyber-vpn.net/` |
| `cyber-vpn.org/api/sub/<redacted>` | `404` for invalid token |

Header check:

```bash
curl -k -sSI https://cyber-vpn.net/ru-RU | egrep -i '^(HTTP/|alt-svc:|strict-transport-security:)'
curl -k -sSI https://admin.cyber-vpn.net/ru-RU/login | egrep -i '^(HTTP/|alt-svc:|strict-transport-security:)'
```

Expected:

```text
alt-svc: h3=":443"; ma=86400
```

---

## 6. Runtime Inventory

Production app host:

```bash
ssh root@45.87.41.146 'docker ps --format "{{.Names}} {{.Status}}" | sort'
```

VPN node:

```bash
ssh root@77.90.13.29 'docker ps --format "{{.Names}} {{.Status}} {{.Ports}}" | sort'
```

Expected VPN node app container:

```text
cybervpn-remnawave-node
```

No application, database, observability, GitLab or payment containers may run on the VPN node.

---

## 7. Observability Checks

Home observability host:

```bash
ssh beep@10.10.10.34 'docker ps --format "{{.Names}} {{.Status}}" | sort'
```

Health probes:

```bash
ssh beep@10.10.10.34 'curl -fsS http://127.0.0.1:9090/-/ready'
ssh beep@10.10.10.34 'curl -fsS http://127.0.0.1:3000/api/health'
ssh beep@10.10.10.34 'curl -fsS http://127.0.0.1:9093/-/ready'
ssh beep@10.10.10.34 'curl -fsS http://127.0.0.1:9000/_health/'
```

Expected:

- Prometheus ready;
- Grafana database `ok`;
- Alertmanager ready;
- Sentry health `ok`;
- GitLab/GitLab Runner containers up.

Customer runtime must not depend on this host being online.

---

## 8. Rollback Check

Check current rollback artifacts:

```bash
ssh root@45.87.41.146 \
  'find /srv/cybervpn/backups -maxdepth 3 \( -name rollback-dry-run.log -o -name rollback-command.txt -o -name rollback.override.yml \) -printf "%TY-%Tm-%Td %TT %p\n" | sort | tail -20'
```

Expected latest status:

```text
rollback_dry_run_status=ok
```

If runtime image inventory changes before canary, repeat rollback dry-run before proceeding.

---

## 9. Owner Manual Canary Checklist

Execute in `S2-STAGE-16`, not during automated rehearsal:

1. owner/internal user opens website;
2. owner/internal user logs in;
3. owner/internal user opens Telegram Bot/Mini App;
4. owner/internal user selects a visible public plan;
5. owner/internal user activates trial or test payment path selected for canary;
6. provisioning completes;
7. `.org` subscription URL is delivered;
8. VPN client imports subscription/config;
9. VPN client connects;
10. support/admin view confirms user/subscription/payment/provisioning status;
11. expiry/renewal/refund behavior is simulated with non-destructive/admin-safe data.

If any step fails, pause cohort expansion and classify the issue before continuing.

---

## 10. No-Go Conditions

Do not proceed to S2 canary if:

- public frontend route returns non-2xx unexpectedly;
- API `/health` is not `ok`;
- API docs become public;
- `.org` serves customer frontend as a mirror;
- VPN node runs anything except node services;
- observability is not reachable and no temporary manual watch is assigned;
- rollback artifact is unavailable;
- HTTP/3/QUIC is disabled;
- payment/trial/provisioning state is changed without evidence;
- any secret appears in committed evidence.

