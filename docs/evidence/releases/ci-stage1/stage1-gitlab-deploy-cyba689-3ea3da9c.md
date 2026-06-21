# Stage 1 GitLab Deploy

Release tag: `cyba689-3ea3da9c`
Commit: `3ea3da9c93eb3560073265505cf6cf4c5308870f`
Pipeline: `local`
Services: `frontend,task-worker,backend,telegram-bot,admin,partner`
Started at: `2026-06-16T19:27:59Z`

[remote-stage1-deploy] current tag: stage1-ci-317-6f1d854e
[remote-stage1-deploy] new tag: cyba689-3ea3da9c
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] building telegram-bot image
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-cyba689-3ea3da9c
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner cybervpn-telegram-bot cybervpn-worker cybervpn-scheduler
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 1.074337 https://cyber-vpn.net/ru-RU
200 1.017312 https://my.cyber-vpn.net/ru-RU/settings
200 0.901358 https://my.cyber-vpn.net/ru-RU/settings/security
200 0.973852 https://my.cyber-vpn.net/ru-RU/settings/delete-account
200 0.654343 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-16T19:47:06Z`
