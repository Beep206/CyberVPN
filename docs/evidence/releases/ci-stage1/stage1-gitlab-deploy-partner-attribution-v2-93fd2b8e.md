# Stage 1 GitLab Deploy

Release tag: `partner-attribution-v2-93fd2b8e`
Commit: `93fd2b8e93aecef6d9bd2e94137b3e13debbb0db`
Pipeline: `local-codex`
Services: `frontend,backend,admin,partner`
Started at: `2026-06-20T06:51:04Z`

[remote-stage1-deploy] current tag: privacy-deletion-1367c20a
[remote-stage1-deploy] new tag: partner-attribution-v2-93fd2b8e
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-partner-attribution-v2-93fd2b8e
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.738531 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.684869 https://admin.cyber-vpn.net/ru-RU/login
200 0.964650 https://partner.cyber-vpn.net/ru-RU/login
200 0.605250 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-20T07:04:46Z`
