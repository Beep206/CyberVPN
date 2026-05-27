# Stage 1 GitLab Deploy

Release tag: `main-growth-admin-subscriptions-20260527T1358`
Commit: `local`
Pipeline: `local`
Services: `backend,telegram-bot,admin`
Started at: `2026-05-27T13:57:51Z`

[remote-stage1-deploy] current tag: admin-2fa-realm-fix-20260527-1825
[remote-stage1-deploy] new tag: main-growth-admin-subscriptions-20260527T1358
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] retagging unchanged frontend image for compose compatibility
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] retagging unchanged partner image for compose compatibility
[remote-stage1-deploy] building telegram-bot image
[remote-stage1-deploy] retagging unchanged task-worker image for compose compatibility
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-growth-admin-subscriptions-20260527T1358
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-admin cybervpn-telegram-bot
[remote-stage1-deploy] compose status
NAME                                      IMAGE                                                                          COMMAND                  SERVICE                 CREATED          STATUS                                     PORTS
cybervpn-stage1-cybervpn-admin-1          cybervpn/cybervpn-admin:main-growth-admin-subscriptions-20260527T1358          "docker-entrypoint.s…"   cybervpn-admin          11 seconds ago   Up 6 seconds (healthy)                     127.0.0.1:13001->3000/tcp
cybervpn-stage1-cybervpn-backend-1        cybervpn/cybervpn-backend:main-growth-admin-subscriptions-20260527T1358        "python -m src.serve"    cybervpn-backend        10 seconds ago   Up Less than a second (health: starting)   127.0.0.1:18080->8000/tcp, 127.0.0.1:19091->9091/tcp
cybervpn-stage1-cybervpn-telegram-bot-1   cybervpn/cybervpn-telegram-bot:main-growth-admin-subscriptions-20260527T1358   "python -m src.main"     cybervpn-telegram-bot   11 seconds ago   Up 6 seconds (health: starting)            127.0.0.1:18088->8080/tcp
[remote-stage1-deploy] backend-health not ready yet (1/30)
[remote-stage1-deploy] backend-health not ready yet (2/30)
[remote-stage1-deploy] backend-health not ready yet (3/30)
[remote-stage1-deploy] backend-health not ready yet (4/30)
[remote-stage1-deploy] backend-health not ready yet (5/30)
[remote-stage1-deploy] backend-health not ready yet (6/30)
{"status":"ok"}
HTTP/1.1 200 OK
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://telegram.org https://*.sentry.io; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://*.sentry.io https://*.ingest.sentry.io https://raw.githack.com https://raw.githubusercontent.com wss: ws:; worker-src 'self' blob:; frame-src 'self' https://oauth.telegram.org; object-src 'none'; base-uri 'self'; form-action 'self'
link: <http://127.0.0.1:13001/ru-RU/login>; rel="alternate"; hreflang="ru-RU", <http://127.0.0.1:13001/en-EN/login>; rel="alternate"; hreflang="en-EN", <http://127.0.0.1:13001/login>; rel="alternate"; hreflang="x-default"
link: </_next/static/media/0acc7fdf55eb3220-s.p.12o-f1.6qra-s.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2", </_next/static/media/70bc3e132a0a741e-s.p.1409xf.ylxg8g.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2", </_next/static/media/c9bd7381a27f2960-s.p.0nt9ayxdmqydo.woff2>; rel=preload; as="font"; crossorigin=""; type="font/woff2"
set-cookie: NEXT_LOCALE=ru-RU; Path=/; SameSite=lax
Vary: rsc, next-router-state-tree, next-router-prefetch, next-router-segment-prefetch, Accept-Encoding
x-nextjs-cache: HIT
x-nextjs-prerender: 1
{"status": "ok", "mode": "webhook", "service": "cybervpn-telegram-bot", "environment": "production"}
[remote-stage1-deploy] deployment complete

## Public Smoke

```text
200 0.686058 https://api.cyber-vpn.net/healthz
200 0.747067 https://admin.cyber-vpn.net/ru-RU/login
200 0.895462 https://my.cyber-vpn.net/ru-RU/referral
```

Completed at: `2026-05-27T14:00:38Z`

## Runtime Growth Flags

```text
backend CHECKOUT_CODE_DISCOUNTS_ENABLED=true
backend GIFT_CODES_ENABLED=true
backend PAYMENT_AUTORENEWAL_ENABLED=false
backend PROMO_CODES_ENABLED=true
backend REFERRAL_ENABLED=true
telegram-bot CRYPTOBOT_ENABLED=false
telegram-bot REFERRAL_ENABLED=true
telegram-bot TELEGRAM_STARS_ENABLED=true
```

## Origin API Smoke

Generated short-lived in-container bearer tokens were used for this smoke. No token values were persisted in evidence.

```text
/referral/status 200
/referral/code 200
/referral/stats 200
/referral/rewards 200
/referral/recent 200
/gifts/my 200
/admin/mobile-users/{customer_id}/customer-subscriptions 200
```
