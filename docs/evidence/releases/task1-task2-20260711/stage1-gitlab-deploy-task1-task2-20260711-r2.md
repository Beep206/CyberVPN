# Stage 1 GitLab Deploy

Release tag: `task1-task2-20260711-r2`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-07-11T13:58:36Z`

[remote-stage1-deploy] current tag: task1-task2-20260711-r1
[remote-stage1-deploy] new tag: task1-task2-20260711-r2
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] retagging unchanged vpn-test-agent image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-task1-task2-20260711-r2
[remote-stage1-deploy] VPN_TEST_AGENT_SECRET is present
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 1.279493 https://cyber-vpn.net/ru-RU/miniapp
200 0.817719 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.719668 https://cyber-vpn.net/runtime/fingerprint
200 1.873456 https://api.cyber-vpn.net/api/v1/runtime/fingerprint
200 0.902911 https://admin.cyber-vpn.net/ru-RU/login
200 0.963141 https://partner.cyber-vpn.net/ru-RU/login
200 0.675828 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-07-11T14:00:33Z`
