# Stage 1 GitLab Deploy

Release tag: `premium-smart-ru-20260628T1650Z`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-06-28T16:54:16Z`

[remote-stage1-deploy] current tag: admin-2fa-fix-20260628T142002Z
[remote-stage1-deploy] new tag: premium-smart-ru-20260628T1650Z
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-premium-smart-ru-20260628T1650Z
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
307 0.568521 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.733023 https://admin.cyber-vpn.net/ru-RU/login
200 0.797581 https://partner.cyber-vpn.net/ru-RU/login
200 0.599058 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-28T16:54:48Z`

## Premium Smart RU Runtime Notes

- Remnawave edge nodes were deployed with `remnawave/node:2.7.0`.
- The Premium Smart RU TZ requested `2.7.4`, but no public
  `remnawave/node:2.7.4` registry tag was available during the 2026-06-28
  rollout. The repository pins `2.7.0` until a newer verified tag exists.
- Runtime verification reported Xray `26.3.27` and connected node API status
  for DE, NL, RU SPB and RU Moscow. RU Moscow uses the tracked control-plane
  IPv4-to-IPv6 proxy unit in `infra/systemd/` because the provider IPv4 API path
  completed TCP handshakes but did not pass application payloads.
