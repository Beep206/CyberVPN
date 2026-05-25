# Stage 1 GitLab Deploy

Release tag: `s3-stage17-controlled-partner-pilot.3`
Commit: `local`
Pipeline: `local`
Services: `backend`
Started at: `2026-05-25T13:41:52Z`

[remote-stage1-deploy] current tag: s3-stage17-controlled-partner-pilot.2
[remote-stage1-deploy] new tag: s3-stage17-controlled-partner-pilot.3
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-s3-stage17-controlled-partner-pilot.3
[remote-stage1-deploy] recreating compose services: cybervpn-backend
[remote-stage1-deploy] compose status
NAME                                 IMAGE                                                             COMMAND                 SERVICE            CREATED         STATUS                                     PORTS
cybervpn-stage1-cybervpn-backend-1   cybervpn/cybervpn-backend:s3-stage17-controlled-partner-pilot.3   "python -m src.serve"   cybervpn-backend   9 seconds ago   Up Less than a second (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
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
200 0.664872 https://api.cyber-vpn.net/healthz
200 0.785452 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.750234 https://admin.cyber-vpn.net/ru-RU/login
200 1.052315 https://cyber-vpn.net/ru-RU/pricing
200 1.526869 https://cyber-vpn.net/ru-RU/status
```

Completed at: `2026-05-25T13:42:23Z`
