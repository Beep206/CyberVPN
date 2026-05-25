# Stage 1 GitLab Deploy

Release tag: `s3-stage17-controlled-partner-pilot.1`
Commit: `local`
Pipeline: `local`
Services: `frontend,backend`
Started at: `2026-05-25T12:51:27Z`

[remote-stage1-deploy] current tag: s3-stage16-disabled-state.3
[remote-stage1-deploy] new tag: s3-stage17-controlled-partner-pilot.1
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-s3-stage17-controlled-partner-pilot.1
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend
[remote-stage1-deploy] compose status
NAME                                  IMAGE                                                              COMMAND                  SERVICE             CREATED          STATUS                                     PORTS
cybervpn-stage1-cybervpn-backend-1    cybervpn/cybervpn-backend:s3-stage17-controlled-partner-pilot.1    "python -m src.serve"    cybervpn-backend    10 seconds ago   Up Less than a second (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
cybervpn-stage1-cybervpn-frontend-1   cybervpn/cybervpn-frontend:s3-stage17-controlled-partner-pilot.1   "docker-entrypoint.s…"   cybervpn-frontend   11 seconds ago   Up 6 seconds (healthy)                     127.0.0.1:13000->3000/tcp
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
