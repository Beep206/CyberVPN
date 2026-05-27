# Stage 1 GitLab Deploy

Release tag: `main-07fd7871-msub08-20260527T061828Z`
Commit: `local`
Pipeline: `local`
Services: `task-worker,backend`
Started at: `2026-05-27T06:18:34Z`

[remote-stage1-deploy] current tag: main-c3dd01d7-msub08-20260527T060914Z
[remote-stage1-deploy] new tag: main-07fd7871-msub08-20260527T061828Z
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-07fd7871-msub08-20260527T061828Z
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-worker cybervpn-scheduler
[remote-stage1-deploy] compose status
NAME                                   IMAGE                                                                 COMMAND                   SERVICE              CREATED          STATUS                                     PORTS
cybervpn-stage1-cybervpn-backend-1     cybervpn/cybervpn-backend:main-07fd7871-msub08-20260527T061828Z       "python -m src.serve"     cybervpn-backend     18 seconds ago   Up Less than a second (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
cybervpn-stage1-cybervpn-scheduler-1   cybervpn/cybervpn-task-worker:main-07fd7871-msub08-20260527T061828Z   "taskiq scheduler sr…"    cybervpn-scheduler   18 seconds ago   Up 6 seconds (health: starting)            
cybervpn-stage1-cybervpn-worker-1      cybervpn/cybervpn-task-worker:main-07fd7871-msub08-20260527T061828Z   "sh -lc 'mkdir -p \"$…"   cybervpn-worker      18 seconds ago   Up 6 seconds (health: starting)            9091/tcp
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
200 0.649935 https://api.cyber-vpn.net/healthz
200 0.953162 https://cyber-vpn.net/ru-RU
200 0.848694 https://my.cyber-vpn.net/ru-RU/dashboard
```

Completed at: `2026-05-27T06:19:12Z`
