# Stage 1 GitLab Deploy

Release tag: `cyba715-8f334661`
Commit: `8f3346613aab0fa7319dd3030832600e4bcc9cd3`
Pipeline: `local`
Services: `frontend,task-worker,backend,telegram-bot,admin,partner`
Started at: `2026-06-18T18:55:16Z`

[remote-stage1-deploy] current tag: cyba689-3ea3da9c
[remote-stage1-deploy] new tag: cyba715-8f334661
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] building telegram-bot image
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-cyba715-8f334661
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner cybervpn-telegram-bot cybervpn-worker cybervpn-scheduler
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.999464 https://cyber-vpn.net/ru-RU
200 0.949657 https://my.cyber-vpn.net/ru-RU/settings
200 0.846002 https://my.cyber-vpn.net/ru-RU/settings/security
200 0.878261 https://my.cyber-vpn.net/ru-RU/settings/delete-account
200 0.647825 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-18T19:13:10Z`
