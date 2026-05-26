# Stage 1 GitLab Deploy

Release tag: `main-ea7a44d4`
Commit: `local`
Pipeline: `local`
Services: `partner`
Started at: `2026-05-26T08:24:45Z`

[remote-stage1-deploy] current tag: main-1ae18f32
[remote-stage1-deploy] new tag: main-ea7a44d4
[remote-stage1-deploy] retagging unchanged backend image for compose compatibility
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-ea7a44d4
[remote-stage1-deploy] recreating compose services: cybervpn-partner
[remote-stage1-deploy] compose status
NAME                                 IMAGE                                     COMMAND                  SERVICE            CREATED         STATUS                                     PORTS
cybervpn-stage1-cybervpn-partner-1   cybervpn/cybervpn-partner:main-ea7a44d4   "docker-entrypoint.s…"   cybervpn-partner   2 seconds ago   Up Less than a second (health: starting)   127.0.0.1:13002->3000/tcp
[remote-stage1-deploy] partner-login not ready yet (1/30)
HTTP/1.1 200 OK
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://telegram.org https://*.sentry.io; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://*.sentry.io https://*.ingest.sentry.io https://raw.githack.com https://raw.githubusercontent.com wss: ws:; worker-src 'self' blob:; frame-src 'self' https://oauth.telegram.org; object-src 'none'; base-uri 'self'; form-action 'self'
link: <http://127.0.0.1:13002/ru-RU/login>; rel="alternate"; hreflang="ru-RU", <http://127.0.0.1:13002/en-EN/login>; rel="alternate"; hreflang="en-EN", <http://127.0.0.1:13002/login>; rel="alternate"; hreflang="x-default"
link: </_next/static/media/0acc7fdf55eb3220-s.p.12o-f1.6qra-s.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2", </_next/static/media/70bc3e132a0a741e-s.p.1409xf.ylxg8g.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2", </_next/static/media/c9bd7381a27f2960-s.p.0nt9ayxdmqydo.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2"
set-cookie: NEXT_LOCALE=ru-RU; Path=/; SameSite=lax
Vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
x-nextjs-stale-time: 300
[remote-stage1-deploy] deployment complete

## Public Smoke

```text
200 0.636951 https://api.cyber-vpn.net/healthz
200 0.912360 https://cyber-vpn.net/ru-RU
200 0.718415 https://admin.cyber-vpn.net/ru-RU/login
```

Completed at: `2026-05-26T08:27:55Z`
