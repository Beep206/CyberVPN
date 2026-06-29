# Stage 1 GitLab Deploy

Release tag: `main-864f0d12-growth-v751-multi-use-invites-20260629`
Commit: `local`
Pipeline: `local`
Services: `frontend,task-worker,backend,telegram-bot,admin,partner`
Started at: `2026-06-29T17:43:01Z`

[remote-stage1-deploy] current tag: main-ae6cc48e-v74-rsc-cors-routing-20260629
[remote-stage1-deploy] new tag: main-864f0d12-growth-v751-multi-use-invites-20260629
[remote-stage1-deploy] building backend image
[remote-stage1-deploy] building frontend image
[remote-stage1-deploy] building admin image
[remote-stage1-deploy] building partner image
[remote-stage1-deploy] building telegram-bot image
[remote-stage1-deploy] building task-worker image
[remote-stage1-deploy] updating compose file from release source
[remote-stage1-deploy] compose backup: /srv/cybervpn/compose/app/docker-compose.yml.pre-main-864f0d12-growth-v751-multi-use-invites-20260629
[remote-stage1-deploy] CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env
[remote-stage1-deploy] recreating compose services: cybervpn-backend cybervpn-frontend cybervpn-admin cybervpn-partner cybervpn-telegram-bot cybervpn-worker cybervpn-scheduler
[remote-stage1-deploy] running backend database migrations

## Public Smoke

```text
200 0.903466 https://cyber-vpn.net/ru-RU/miniapp
200 0.749457 https://cyber-vpn.net/ru-RU/miniapp/home
200 0.634561 https://cyber-vpn.net/runtime/fingerprint
200 0.106844 https://api.cyber-vpn.net/api/v1/runtime/fingerprint
200 0.706594 https://admin.cyber-vpn.net/ru-RU/login
200 0.923621 https://partner.cyber-vpn.net/ru-RU/login
200 0.551705 https://api.cyber-vpn.net/healthz
```

## Customer RSC Smoke

```text
RSC route smoke host=https://my.cyber-vpn.net locales=en-EN ru-RU
PASS RSC https://my.cyber-vpn.net/en-EN/dashboard?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/dashboard?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/subscriptions?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/subscriptions?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/payment-history?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/payment-history?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/referral?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/referral?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/rewards?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/rewards/referral?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards/referral?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/rewards/gifts?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards/gifts?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/rewards/codes?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards/codes?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/rewards/notifications?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards/notifications?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/messages?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/messages?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/wallet?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/wallet?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/settings?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/settings?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/support?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/support?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/servers?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/servers?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/onboarding?_rsc=customer-site-smoke http=404
PASS OPTIONS https://my.cyber-vpn.net/en-EN/onboarding?_rsc=customer-site-smoke http=404
PASS RSC https://my.cyber-vpn.net/en-EN/monitoring?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/monitoring?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/analytics?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/analytics?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/users?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/users?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/partner?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/partner?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/dashboard?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/dashboard?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/subscriptions?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/subscriptions?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/payment-history?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/payment-history?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/referral?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/referral?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards/referral?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards/referral?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards/gifts?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards/gifts?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards/invites?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards/invites?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards/codes?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards/codes?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards/notifications?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards/notifications?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/messages?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/messages?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/wallet?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/wallet?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/settings?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/settings?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/support?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/support?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/servers?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/servers?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/onboarding?_rsc=customer-site-smoke http=404
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/onboarding?_rsc=customer-site-smoke http=404
PASS RSC https://my.cyber-vpn.net/ru-RU/monitoring?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/monitoring?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/analytics?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/analytics?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/users?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/users?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/partner?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/partner?_rsc=customer-site-smoke http=400
```

Completed at: `2026-06-29T18:01:52Z`
