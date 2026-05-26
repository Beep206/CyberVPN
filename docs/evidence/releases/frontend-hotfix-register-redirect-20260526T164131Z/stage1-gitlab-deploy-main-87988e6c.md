# Stage 1 GitLab Deploy

Release tag: `main-87988e6c`
Commit: `local`
Pipeline: `local`
Services: `frontend`
Started at: `2026-05-26T16:41:37Z`

[remote-stage1-deploy] current tag: main-e08f1428
[remote-stage1-deploy] new tag: main-87988e6c
[remote-stage1-deploy] retagging unchanged backend image for compose compatibility
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] retagging unchanged admin image for compose compatibility
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] retagging unchanged telegram-bot image for compose compatibility
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-87988e6c
[remote-stage1-deploy] recreating compose services: cybervpn-frontend
[remote-stage1-deploy] compose status
NAME                                  IMAGE                                      COMMAND                  SERVICE             CREATED         STATUS                                     PORTS
cybervpn-stage1-cybervpn-frontend-1   cybervpn/cybervpn-frontend:main-87988e6c   "docker-entrypoint.s…"   cybervpn-frontend   3 seconds ago   Up Less than a second (health: starting)   127.0.0.1:13000->3000/tcp
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
200 0.754301 https://cyber-vpn.net/ru-RU/register
200 0.761698 https://cyber-vpn.net/ru-RU/verify?email=smoke%40cyber-vpn.net
200 0.713887 https://cyber-vpn.net/ru-RU/login
200 0.976800 https://my.cyber-vpn.net/ru-RU/register
200 1.748193 https://my.cyber-vpn.net/ru-RU/verify?email=smoke%40cyber-vpn.net
200 0.799603 https://my.cyber-vpn.net/ru-RU/login
```

Completed at: `2026-05-26T16:47:35Z`

## Post-Deploy Verification

```text
Frontend container:
cybervpn-stage1-cybervpn-frontend-1 cybervpn/cybervpn-frontend:main-87988e6c Up healthy 127.0.0.1:13000->3000/tcp

Cloudflare/public edge:
HTTP/2 200
alt-svc: h3=":443"; ma=86400
cf-cache-status: DYNAMIC
server: cloudflare

Frontend log scan:
No EACCES/error/exception/fatal/warn/denied/failed/405 entries found in the new frontend container logs during the post-deploy window.
```
