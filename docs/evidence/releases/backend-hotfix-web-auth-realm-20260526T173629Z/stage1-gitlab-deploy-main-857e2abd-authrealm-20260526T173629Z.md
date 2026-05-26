# Stage 1 GitLab Deploy

Release tag: `main-857e2abd-authrealm-20260526T173629Z`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-05-26T17:36:36Z`

[remote-stage1-deploy] current tag: main-87988e6c
[remote-stage1-deploy] new tag: main-857e2abd-authrealm-20260526T173629Z
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-857e2abd-authrealm-20260526T173629Z
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] compose status
NAME                                 IMAGE                                                                COMMAND                 SERVICE            CREATED          STATUS                                     PORTS
cybervpn-stage1-cybervpn-backend-1   cybervpn/cybervpn-backend:main-857e2abd-authrealm-20260526T173629Z   "python -m src.serve"   cybervpn-backend   12 seconds ago   Up Less than a second (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
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
200 0.653335 https://api.cyber-vpn.net/health
200 1.019118 https://cyber-vpn.net/ru-RU/login
200 1.000606 https://my.cyber-vpn.net/ru-RU/dashboard
200 0.788461 https://admin.cyber-vpn.net/ru-RU/login
```

Completed at: `2026-05-26T17:37:09Z`
