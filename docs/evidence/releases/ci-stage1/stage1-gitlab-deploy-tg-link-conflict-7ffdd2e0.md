# Stage 1 GitLab Deploy

Release tag: `tg-link-conflict-7ffdd2e0`
Commit: `7ffdd2e0ba067e3b8c69fac6ebd9116bb6dab858`
Pipeline: `local-codex`
Services: `backend`
Started at: `2026-06-19T14:00:27Z`

[remote-stage1-deploy] current tag: tg-link-97effff5
[remote-stage1-deploy] new tag: tg-link-conflict-7ffdd2e0
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-tg-link-conflict-7ffdd2e0
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.755639 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.692465 https://admin.cyber-vpn.net/ru-RU/login
200 0.848043 https://partner.cyber-vpn.net/ru-RU/login
200 0.589645 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-19T14:00:55Z`
