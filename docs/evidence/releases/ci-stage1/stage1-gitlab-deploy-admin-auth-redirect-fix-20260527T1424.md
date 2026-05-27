# Stage 1 GitLab Deploy

Release tag: `admin-auth-redirect-fix-20260527T1424`
Commit: `local`
Pipeline: `local`
Services: `admin`
Started at: `2026-05-27T14:15:57Z`

[remote-stage1-deploy] current tag: admin-auth-redirect-fix-20260527T1416
[remote-stage1-deploy] new tag: admin-auth-redirect-fix-20260527T1424
[remote-stage1-deploy] retagging unchanged backend image for compose compatibility
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-admin-auth-redirect-fix-20260527T1424
[remote-stage1-deploy] recreating compose services: cybervpn-admin
[remote-stage1-deploy] compose status
NAME                               IMAGE                                                           COMMAND                  SERVICE          CREATED         STATUS                                     PORTS
cybervpn-stage1-cybervpn-admin-1   cybervpn/cybervpn-admin:admin-auth-redirect-fix-20260527T1424   "docker-entrypoint.s…"   cybervpn-admin   2 seconds ago   Up Less than a second (health: starting)   127.0.0.1:13001->3000/tcp
[remote-stage1-deploy] admin-login not ready yet (1/30)
HTTP/1.1 200 OK
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://telegram.org https://*.sentry.io; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://*.sentry.io https://*.ingest.sentry.io https://raw.githack.com https://raw.githubusercontent.com wss: ws:; worker-src 'self' blob:; frame-src 'self' https://oauth.telegram.org; object-src 'none'; base-uri 'self'; form-action 'self'
link: <http://127.0.0.1:13001/ru-RU/login>; rel="alternate"; hreflang="ru-RU", <http://127.0.0.1:13001/en-EN/login>; rel="alternate"; hreflang="en-EN", <http://127.0.0.1:13001/login>; rel="alternate"; hreflang="x-default"
link: </_next/static/media/0acc7fdf55eb3220-s.p.12o-f1.6qra-s.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2", </_next/static/media/70bc3e132a0a741e-s.p.1409xf.ylxg8g.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2", </_next/static/media/c9bd7381a27f2960-s.p.0nt9ayxdmqydo.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2"
set-cookie: NEXT_LOCALE=ru-RU; Path=/; SameSite=lax
Vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
x-nextjs-cache: HIT
[remote-stage1-deploy] deployment complete

## Public Smoke

```text
200 0.785876 https://admin.cyber-vpn.net/ru-RU/login
200 1.731805 https://admin.cyber-vpn.net/ru-RU/customers/7d871bc5-af6c-49b2-a3e6-e77eec938021
```

Completed at: `2026-05-27T14:18:16Z`

## Post-Deploy Runtime Check

```text
CYBERVPN_IMAGE_TAG=admin-auth-redirect-fix-20260527T1424
cybervpn-stage1-cybervpn-admin-1 cybervpn/cybervpn-admin:admin-auth-redirect-fix-20260527T1424 Up (healthy)
```
