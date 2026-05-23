# Stage 1 GitLab Deploy

Release tag: `stage2-public-rc.5`
Commit: `3c3a7b1a95019252e91550ffb08e754bbc794c98`
Pipeline: `local`
Services: `frontend,task-worker,backend,telegram-bot,admin`
Started at: `2026-05-23T08:59:55Z`

[remote-stage1-deploy] current tag: stage1-direct-suburl-refresh-20260522T091303Z
[remote-stage1-deploy] new tag: stage2-public-rc.5
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building telegram-bot image
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-telegram-bot cybervpn-worker cybervpn-scheduler
[remote-stage1-deploy] compose status
NAME                                      IMAGE                                               COMMAND                   SERVICE                 CREATED          STATUS                            PORTS
cybervpn-stage1-cybervpn-admin-1          cybervpn/cybervpn-admin:stage2-public-rc.5          "docker-entrypoint.s…"    cybervpn-admin          14 seconds ago   Up 3 seconds (health: starting)   127.0.0.1:13001->3000/tcp
cybervpn-stage1-cybervpn-backend-1        cybervpn/cybervpn-backend:stage2-public-rc.5        "python -m src.serve"     cybervpn-backend        14 seconds ago   Up 3 seconds (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
cybervpn-stage1-cybervpn-frontend-1       cybervpn/cybervpn-frontend:stage2-public-rc.5       "docker-entrypoint.s…"    cybervpn-frontend       14 seconds ago   Up 3 seconds (health: starting)   127.0.0.1:13000->3000/tcp
cybervpn-stage1-cybervpn-scheduler-1      cybervpn/cybervpn-task-worker:stage2-public-rc.5    "taskiq scheduler sr…"    cybervpn-scheduler      14 seconds ago   Up 3 seconds (health: starting)
cybervpn-stage1-cybervpn-telegram-bot-1   cybervpn/cybervpn-telegram-bot:stage2-public-rc.5   "python -m src.main"      cybervpn-telegram-bot   14 seconds ago   Up 3 seconds (health: starting)   127.0.0.1:18088->8080/tcp
cybervpn-stage1-cybervpn-worker-1         cybervpn/cybervpn-task-worker:stage2-public-rc.5    "sh -lc 'mkdir -p \"$…"   cybervpn-worker         14 seconds ago   Up 3 seconds (health: starting)   9091/tcp
[remote-stage1-deploy] backend-health not ready yet (1/30)
[remote-stage1-deploy] backend-health not ready yet (2/30)
[remote-stage1-deploy] backend-health not ready yet (3/30)
[remote-stage1-deploy] backend-health not ready yet (4/30)
[remote-stage1-deploy] backend-health not ready yet (5/30)
[remote-stage1-deploy] backend-health not ready yet (6/30)
[remote-stage1-deploy] backend-health not ready yet (7/30)
[remote-stage1-deploy] backend-health not ready yet (8/30)
[remote-stage1-deploy] backend-health not ready yet (9/30)
[remote-stage1-deploy] backend-health not ready yet (10/30)
[remote-stage1-deploy] backend-health not ready yet (11/30)
[remote-stage1-deploy] backend-health not ready yet (12/30)
[remote-stage1-deploy] backend-health not ready yet (13/30)
[remote-stage1-deploy] backend-health not ready yet (14/30)
[remote-stage1-deploy] backend-health not ready yet (15/30)
[remote-stage1-deploy] backend-health not ready yet (16/30)
[remote-stage1-deploy] backend-health not ready yet (17/30)
[remote-stage1-deploy] backend-health not ready yet (18/30)
[remote-stage1-deploy] backend-health not ready yet (19/30)
[remote-stage1-deploy] backend-health not ready yet (20/30)
[remote-stage1-deploy] backend-health not ready yet (21/30)
[remote-stage1-deploy] backend-health not ready yet (22/30)
[remote-stage1-deploy] backend-health not ready yet (23/30)
[remote-stage1-deploy] backend-health not ready yet (24/30)
[remote-stage1-deploy] backend-health not ready yet (25/30)
[remote-stage1-deploy] backend-health not ready yet (26/30)
[remote-stage1-deploy] backend-health not ready yet (27/30)
[remote-stage1-deploy] backend-health not ready yet (28/30)
[remote-stage1-deploy] backend-health not ready yet (29/30)
[remote-stage1-deploy] backend-health not ready yet (30/30)
[remote-stage1-deploy] backend-health did not become ready
