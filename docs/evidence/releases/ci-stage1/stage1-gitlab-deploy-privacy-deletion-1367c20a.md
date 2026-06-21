# Stage 1 GitLab Deploy

Release tag: `privacy-deletion-1367c20a`
Commit: `1367c20ad05544972a8f4e0283aecabc9320d764`
Pipeline: `local-codex`
Services: `frontend,backend,admin,partner`
Started at: `2026-06-19T19:06:58Z`

[remote-stage1-deploy] current tag: privacy-deletion-33186b40
[remote-stage1-deploy] new tag: privacy-deletion-1367c20a
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-privacy-deletion-1367c20a
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.747810 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.784715 https://admin.cyber-vpn.net/ru-RU/login
200 0.903758 https://partner.cyber-vpn.net/ru-RU/login
200 0.562064 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-06-19T19:07:32Z`
