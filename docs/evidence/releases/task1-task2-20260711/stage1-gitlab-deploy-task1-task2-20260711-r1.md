# Stage 1 GitLab Deploy

Release tag: `task1-task2-20260711-r1`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-07-11T12:51:33Z`

[remote-stage1-deploy] current tag: main-484c7487-service-access-repair-20260709T165614Z
[remote-stage1-deploy] new tag: task1-task2-20260711-r1
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] retagging unchanged vpn-test-agent image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-task1-task2-20260711-r1
[remote-stage1-deploy] VPN_TEST_AGENT_SECRET is present
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 1.380162 https://cyber-vpn.net/ru-RU/miniapp
200 0.902543 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.726410 https://cyber-vpn.net/runtime/fingerprint
200 2.606830 https://api.cyber-vpn.net/api/v1/runtime/fingerprint
200 1.118256 https://admin.cyber-vpn.net/ru-RU/login
200 0.869233 https://partner.cyber-vpn.net/ru-RU/login
200 0.677311 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-07-11T12:52:19Z`
