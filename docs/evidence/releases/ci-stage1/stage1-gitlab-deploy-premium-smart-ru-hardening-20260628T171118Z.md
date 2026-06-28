# Stage 1 GitLab Deploy

Release tag: `premium-smart-ru-hardening-20260628T171118Z`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-06-28T17:11:55Z`

[remote-stage1-deploy] current tag: premium-smart-ru-20260628T1650Z
[remote-stage1-deploy] new tag: premium-smart-ru-hardening-20260628T171118Z
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-premium-smart-ru-hardening-20260628T171118Z
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
307 0.550035 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.701466 https://admin.cyber-vpn.net/ru-RU/login
200 0.910458 https://partner.cyber-vpn.net/ru-RU/login
200 0.555548 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-28T17:12:28Z`
