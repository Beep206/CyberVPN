# Stage 1 GitLab Deploy

Release tag: `main-a0feffef-servers-config-20260526T183351Z`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-05-26T18:33:58Z`

[remote-stage1-deploy] current tag: main-c2207460-cabinet-api-20260526T182000Z
[remote-stage1-deploy] new tag: main-a0feffef-servers-config-20260526T183351Z
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-a0feffef-servers-config-20260526T183351Z
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] compose status
NAME                                 IMAGE                                                                     COMMAND                 SERVICE            CREATED         STATUS                                     PORTS
cybervpn-stage1-cybervpn-backend-1   cybervpn/cybervpn-backend:main-a0feffef-servers-config-20260526T183351Z   "python -m src.serve"   cybervpn-backend   9 seconds ago   Up Less than a second (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
[remote-stage1-deploy] backend-health not ready yet (1/30)
[remote-stage1-deploy] backend-health not ready yet (2/30)
[remote-stage1-deploy] backend-health not ready yet (3/30)
[remote-stage1-deploy] backend-health not ready yet (4/30)
[remote-stage1-deploy] backend-health not ready yet (5/30)
[remote-stage1-deploy] backend-health not ready yet (6/30)
{"status":"ok"}
[remote-stage1-deploy] deployment complete

## Public Smoke

```text
200 0.862764 https://api.cyber-vpn.net/health
200 1.931588 https://my.cyber-vpn.net/ru-RU/servers
200 0.803862 https://my.cyber-vpn.net/ru-RU/dashboard
```

Completed at: `2026-05-26T18:34:29Z`
