# Stage 1 GitLab Deploy

Release tag: `main-6865e021-growth-v72-lifetime-20260629`
Commit: `6865e02195e9643016f6d491e5bc60f084dea56d`
Pipeline: `local`
Services: `frontend,task-worker,backend,telegram-bot,admin,partner`
Started at: `2026-06-29T08:38:28Z`

[remote-stage1-deploy] current tag: stage1-beta-rc.2
[remote-stage1-deploy] new tag: main-6865e021-growth-v72-lifetime-20260629
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] building telegram-bot image
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn-h/compose/app/docker-compose.yml.pre-main-6865e021-growth-v72-lifetime-20260629
[remote-stage1-deploy] created CYBERVPN_DEVICE_COOKIE_PEPPER in backend app.env; backup: /srv/cybervpn-h/secrets/app.env.pre-device-cookie-pepper-20260629T085602Z
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner cybervpn-telegram-bot cybervpn-worker cybervpn-scheduler

## Manual Recovery

The deploy script built images as `cybervpn/cybervpn-*`, while the Stage 1
compose file expects `local/cybervpn-*`. Recovery retagged the already-built
images to the compose image names, removed only stale app-layer containers
(`backend`, `frontend`, `admin`, `partner`, `telegram-bot`, `worker`,
`scheduler`, `nats`), and recreated the app services without touching
PostgreSQL, Valkey/Redis, Remnawave, or exporter containers.

Runtime production guards then failed closed on placeholder or absent runtime
values that had existed in the server configuration. Recovery updated the
production runtime secret files with generated or existing operational values
without printing secrets:

- disabled Google/GitHub OAuth login providers until real provider credentials
  are present;
- generated real `PAYMENT_SETTLEMENT_WORKER_SECRET`;
- generated real shared `TELEGRAM_BOT_INTERNAL_SECRET`;
- generated real shared `BACKEND_INTERNAL_SECRET`;
- copied existing operational SMTP host/port/auth source into task-worker
  runtime env and configured verified sender domains.

The local deploy script default image registry was corrected from `cybervpn`
to `local` after this recovery to prevent the same compose/image mismatch on
future runs.

## Final Runtime Evidence

```text
docker compose ps:
cybervpn-admin                  local/cybervpn-admin:main-6865e021-growth-v72-lifetime-20260629          healthy
cybervpn-backend                local/cybervpn-backend:main-6865e021-growth-v72-lifetime-20260629        healthy
cybervpn-frontend               local/cybervpn-frontend:main-6865e021-growth-v72-lifetime-20260629       healthy
cybervpn-nats                   nats:2.12.7-alpine                                                       healthy
cybervpn-partner                local/cybervpn-partner:main-6865e021-growth-v72-lifetime-20260629        healthy
cybervpn-scheduler              local/cybervpn-task-worker:main-6865e021-growth-v72-lifetime-20260629    healthy
cybervpn-telegram-bot           local/cybervpn-telegram-bot:main-6865e021-growth-v72-lifetime-20260629   healthy
cybervpn-worker                 local/cybervpn-task-worker:main-6865e021-growth-v72-lifetime-20260629    healthy

alembic current:
20260629_invite_lifetime_v72 (head)

public smoke:
api_health 200 0.544551
my_dashboard 200 0.864352
admin_login 200 0.669040
partner_login 200 0.868319

local smoke:
local_backend 200 0.006921
frontend /ru-RU/miniapp/home 200
admin /ru-RU/login 200
partner /ru-RU/login 200
```
