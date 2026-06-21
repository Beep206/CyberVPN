# Stage 1 GitLab Deploy

Release tag: `partner-attribution-remaining-5db6c17e`
Commit: `5db6c17e9d13e072930c6419550a5895a681bf25`
Pipeline: `local-codex`
Services: `backend`
Started at: `2026-06-20T14:58:50Z`

[remote-stage1-deploy] current tag: admin-privacy-i18n-b77d52bc
[remote-stage1-deploy] new tag: partner-attribution-remaining-5db6c17e
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-partner-attribution-remaining-5db6c17e
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.949555 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.845921 https://admin.cyber-vpn.net/ru-RU/login
200 0.906761 https://partner.cyber-vpn.net/ru-RU/login
200 0.574310 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-20T14:59:19Z`
