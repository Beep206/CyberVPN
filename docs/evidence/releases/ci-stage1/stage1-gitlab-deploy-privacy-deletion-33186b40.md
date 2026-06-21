# Stage 1 GitLab Deploy

Release tag: `privacy-deletion-33186b40`
Commit: `33186b40d519c1273c0688a03d3284ec80829379`
Pipeline: `local-codex`
Services: `frontend,backend,admin,partner`
Started at: `2026-06-19T18:52:47Z`

[remote-stage1-deploy] current tag: referral-attribution-1f61daf2
[remote-stage1-deploy] new tag: privacy-deletion-33186b40
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-privacy-deletion-33186b40
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner
[remote-stage1-deploy] running backend database migrations
