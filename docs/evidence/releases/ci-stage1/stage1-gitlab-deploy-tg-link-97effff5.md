# Stage 1 GitLab Deploy

Release tag: `tg-link-97effff5`
Commit: `97effff50c04a3720ed34414ab45f73f56c76820`
Pipeline: `local-codex`
Services: `backend`
Started at: `2026-06-19T12:48:35Z`

[remote-stage1-deploy] current tag: cyba715-8f334661
[remote-stage1-deploy] new tag: tg-link-97effff5
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-tg-link-97effff5
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.798092 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.685412 https://admin.cyber-vpn.net/ru-RU/login
200 0.873999 https://partner.cyber-vpn.net/ru-RU/login
200 0.576148 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-19T12:49:04Z`
