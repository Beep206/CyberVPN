# Stage 1 GitLab Deploy

Release tag: `main-c2d0fc2b`
Commit: `local`
Pipeline: `local`
Services: `frontend,task-worker`
Started at: `2026-05-25T20:54:45Z`

[remote-stage1-deploy] current tag: main-ba9c4448
[remote-stage1-deploy] new tag: main-c2d0fc2b
[remote-stage1-deploy] retagging unchanged backend image for compose compatibility
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-c2d0fc2b
[remote-stage1-deploy] recreating compose services: cybervpn-frontend cybervpn-worker cybervpn-scheduler
[remote-stage1-deploy] compose status
NAME                                   IMAGE                                         COMMAND                   SERVICE              CREATED          STATUS                           PORTS
cybervpn-stage1-cybervpn-frontend-1    cybervpn/cybervpn-frontend:main-c2d0fc2b      "docker-entrypoint.s…"    cybervpn-frontend    12 seconds ago   Up 1 second (health: starting)   127.0.0.1:13000->3000/tcp
cybervpn-stage1-cybervpn-scheduler-1   cybervpn/cybervpn-task-worker:main-c2d0fc2b   "taskiq scheduler sr…"    cybervpn-scheduler   12 seconds ago   Up 1 second (health: starting)   
cybervpn-stage1-cybervpn-worker-1      cybervpn/cybervpn-task-worker:main-c2d0fc2b   "sh -lc 'mkdir -p \"$…"   cybervpn-worker      12 seconds ago   Up 1 second (health: starting)   9091/tcp
[remote-stage1-deploy] frontend-miniapp not ready yet (1/30)
HTTP/1.1 200 OK
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://telegram.org https://*.sentry.io; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://*.sentry.io https://*.ingest.sentry.io https://raw.githack.com https://raw.githubusercontent.com wss: ws:; worker-src 'self' blob:; frame-src 'self' https://oauth.telegram.org; object-src 'none'; base-uri 'self'; form-action 'self'
link: <http://127.0.0.1:13000/en-EN/miniapp/home>; rel="alternate"; hreflang="en-EN", <http://127.0.0.1:13000/ru-RU/miniapp/home>; rel="alternate"; hreflang="ru-RU", <http://127.0.0.1:13000/zh-CN/miniapp/home>; rel="alternate"; hreflang="zh-CN", <http://127.0.0.1:13000/hi-IN/miniapp/home>; rel="alternate"; hreflang="hi-IN", <http://127.0.0.1:13000/id-ID/miniapp/home>; rel="alternate"; hreflang="id-ID", <http://127.0.0.1:13000/vi-VN/miniapp/home>; rel="alternate"; hreflang="vi-VN", <http://127.0.0.1:13000/th-TH/miniapp/home>; rel="alternate"; hreflang="th-TH", <http://127.0.0.1:13000/ja-JP/miniapp/home>; rel="alternate"; hreflang="ja-JP", <http://127.0.0.1:13000/ko-KR/miniapp/home>; rel="alternate"; hreflang="ko-KR", <http://127.0.0.1:13000/ar-SA/miniapp/home>; rel="alternate"; hreflang="ar-SA", <http://127.0.0.1:13000/fa-IR/miniapp/home>; rel="alternate"; hreflang="fa-IR", <http://127.0.0.1:13000/tr-TR/miniapp/home>; rel="alternate"; hreflang="tr-TR", <http://127.0.0.1:13000/ur-PK/miniapp/home>; rel="alternate"; hreflang="ur-PK", <http://127.0.0.1:13000/bn-BD/miniapp/home>; rel="alternate"; hreflang="bn-BD", <http://127.0.0.1:13000/ms-MY/miniapp/home>; rel="alternate"; hreflang="ms-MY", <http://127.0.0.1:13000/es-ES/miniapp/home>; rel="alternate"; hreflang="es-ES", <http://127.0.0.1:13000/kk-KZ/miniapp/home>; rel="alternate"; hreflang="kk-KZ", <http://127.0.0.1:13000/be-BY/miniapp/home>; rel="alternate"; hreflang="be-BY", <http://127.0.0.1:13000/my-MM/miniapp/home>; rel="alternate"; hreflang="my-MM", <http://127.0.0.1:13000/uz-UZ/miniapp/home>; rel="alternate"; hreflang="uz-UZ", <http://127.0.0.1:13000/ha-NG/miniapp/home>; rel="alternate"; hreflang="ha-NG", <http://127.0.0.1:13000/yo-NG/miniapp/home>; rel="alternate"; hreflang="yo-NG", <http://127.0.0.1:13000/ku-IQ/miniapp/home>; rel="alternate"; hreflang="ku-IQ", <http://127.0.0.1:13000/am-ET/miniapp/home>; rel="alternate"; hreflang="am-ET", <http://127.0.0.1:13000/fr-FR/miniapp/home>; rel="alternate"; hreflang="fr-FR", <http://127.0.0.1:13000/tk-TM/miniapp/home>; rel="alternate"; hreflang="tk-TM", <http://127.0.0.1:13000/zh-Hant/miniapp/home>; rel="alternate"; hreflang="zh-Hant", <http://127.0.0.1:13000/he-IL/miniapp/home>; rel="alternate"; hreflang="he-IL", <http://127.0.0.1:13000/de-DE/miniapp/home>; rel="alternate"; hreflang="de-DE", <http://127.0.0.1:13000/pt-PT/miniapp/home>; rel="alternate"; hreflang="pt-PT", <http://127.0.0.1:13000/it-IT/miniapp/home>; rel="alternate"; hreflang="it-IT", <http://127.0.0.1:13000/nl-NL/miniapp/home>; rel="alternate"; hreflang="nl-NL", <http://127.0.0.1:13000/pl-PL/miniapp/home>; rel="alternate"; hreflang="pl-PL", <http://127.0.0.1:13000/fil-PH/miniapp/home>; rel="alternate"; hreflang="fil-PH", <http://127.0.0.1:13000/uk-UA/miniapp/home>; rel="alternate"; hreflang="uk-UA", <http://127.0.0.1:13000/cs-CZ/miniapp/home>; rel="alternate"; hreflang="cs-CZ", <http://127.0.0.1:13000/ro-RO/miniapp/home>; rel="alternate"; hreflang="ro-RO", <http://127.0.0.1:13000/hu-HU/miniapp/home>; rel="alternate"; hreflang="hu-HU", <http://127.0.0.1:13000/sv-SE/miniapp/home>; rel="alternate"; hreflang="sv-SE", <http://127.0.0.1:13000/miniapp/home>; rel="alternate"; hreflang="x-default"
set-cookie: NEXT_LOCALE=ru-RU; Path=/; SameSite=lax
Vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
x-nextjs-cache: HIT
x-nextjs-prerender: 1
[remote-stage1-deploy] deployment complete

## Public Smoke

```text
200 0.577981 https://api.cyber-vpn.net/healthz
200 1.129227 https://cyber-vpn.net/ru-RU
200 0.788912 https://cyber-vpn.net/ru-RU/register
200 0.750886 https://cyber-vpn.net/ru-RU/verify
200 0.998541 https://cyber-vpn.net/ru-RU/pricing
200 0.801524 https://cyber-vpn.net/ru-RU/miniapp/home
```

Completed at: `2026-05-25T20:58:44Z`

## Post-Deploy Health

Runtime services reached healthy state after recreation:

```text
cybervpn-frontend:  cybervpn/cybervpn-frontend:main-c2d0fc2b      healthy
cybervpn-scheduler: cybervpn/cybervpn-task-worker:main-c2d0fc2b   healthy
cybervpn-worker:    cybervpn/cybervpn-task-worker:main-c2d0fc2b   healthy
```

External route checks for registration and OTP verification returned `HTTP/2 200` and preserved HTTP/3 advertisement:

```text
https://cyber-vpn.net/ru-RU/register  HTTP/2 200, alt-svc: h3=":443"; ma=86400
https://cyber-vpn.net/ru-RU/verify    HTTP/2 200, alt-svc: h3=":443"; ma=86400
```
