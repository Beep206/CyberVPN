# Stage 1 GitLab Deploy

Release tag: `referral-attribution-1f61daf2`
Commit: `1f61daf2ac1ddfc8a06b4ee1f4c28595ed229f38`
Pipeline: `local-codex`
Services: `frontend,backend,admin,partner`
Started at: `2026-06-19T17:20:28Z`

[remote-stage1-deploy] current tag: redirect-port-fix-760044d3
[remote-stage1-deploy] new tag: referral-attribution-1f61daf2
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-referral-attribution-1f61daf2
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.763426 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.742732 https://admin.cyber-vpn.net/ru-RU/login
200 0.858596 https://partner.cyber-vpn.net/ru-RU/login
200 0.645636 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-19T17:33:19Z`
