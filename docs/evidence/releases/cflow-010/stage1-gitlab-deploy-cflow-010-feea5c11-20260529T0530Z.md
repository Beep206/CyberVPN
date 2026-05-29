# Stage 1 GitLab Deploy

Release tag: `cflow-010-feea5c11-20260529T0530Z`
Commit: `local`
Pipeline: `local`
Services: `admin`
Started at: `2026-05-29T05:30:42Z`

[remote-stage1-deploy] current tag: cflow-010-admin-payments-91af2373-20260529T0523Z
[remote-stage1-deploy] new tag: cflow-010-feea5c11-20260529T0530Z
[remote-stage1-deploy] retagging unchanged backend image for compose compatibility
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-cflow-010-feea5c11-20260529T0530Z
[remote-stage1-deploy] recreating compose services: cybervpn-admin
[remote-stage1-deploy] compose status
NAME                               IMAGE                                                       COMMAND                  SERVICE          CREATED        STATUS                                     PORTS
cybervpn-stage1-cybervpn-admin-1   cybervpn/cybervpn-admin:cflow-010-feea5c11-20260529T0530Z   "docker-entrypoint.s…"   cybervpn-admin   1 second ago   Up Less than a second (health: starting)   127.0.0.1:13001->3000/tcp
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
200 0.786703 https://admin.cyber-vpn.net/ru-RU/login
200 0.883338 https://admin.cyber-vpn.net/ru-RU/dashboard
200 0.728837 https://my.cyber-vpn.net/ru-RU/login
200 0.655836 https://api.cyber-vpn.net/healthz
```

Completed at: `2026-05-29T05:30:53Z`
