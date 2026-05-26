# S3 Partner Public Runtime Deploy Evidence

Date: `2026-05-26`

Runtime commit: `ea7a44d4`

Release tag: `main-ea7a44d4`

Scope:

- Deployed S3 partner runtime as a separate `cybervpn-partner` container.
- Added `partner` as a first-class target to `scripts/deploy/stage1-gitlab-deploy.sh`.
- Kept existing S1/S2 runtime services in place; the deploy script retagged unchanged images for compose compatibility.
- Published partner portal at `https://partner.cyber-vpn.net`.
- Kept `https://cyber-vpn.net/.../partner` and `https://my.cyber-vpn.net/.../partner` redirected to the partner subdomain.
- Kept HTTP/3/QUIC enabled in Caddy and Cloudflare.

## Code And Push

- GitLab first push: `main -> main`, `5047d8d2..ea7a44d4`.
- GitHub mirror push: `main -> main`, `5047d8d2..ea7a44d4`.

## Local Validation

- `npm run lint -w partner`: passed.
- `npm run build -w partner`: passed with production env for `partner.cyber-vpn.net`.
- `bash -n scripts/deploy/stage1-gitlab-deploy.sh`: passed.
- `STAGE1_DEPLOY_DRY_RUN=true ... stage1-gitlab-deploy.sh partner`: passed.
- `docker compose -f infra/deploy/stage1/docker-compose.stage1.yml config --services`: passed and includes `cybervpn-partner`.
- `git diff --check`: passed.
- Secret scan over changed deploy/partner files: no live secret introduced.
- `npm audit --workspace partner --audit-level=high`: passed high threshold; remaining known issue is moderate `postcss` under `next`, with npm suggesting a breaking forced downgrade path, so no automatic change was applied.

Known local test limitation:

- `vitest run src/features/storefront-shell/lib/runtime.test.ts` did not reach tests because Vitest/jsdom fails before test execution on the current Node/tooling graph: `cssstyle` requires `@asamuzakjp/css-color` ESM with top-level await. This is a test-runner/tooling issue, not a runtime build failure.

## Production Deploy

Deploy evidence file:

- `docs/evidence/releases/s3-partner-public-deploy-20260526T082440Z/stage1-gitlab-deploy-main-ea7a44d4.md`

Production container state:

```text
cybervpn-stage1-cybervpn-partner-1
image: cybervpn/cybervpn-partner:main-ea7a44d4
status: healthy
port: 127.0.0.1:13002 -> 3000
```

Internal smoke:

```text
http://127.0.0.1:13002/ru-RU/login -> 200
```

## DNS And TLS

Cloudflare DNS:

```text
partner.cyber-vpn.net A 45.87.41.146 proxied=true
```

Origin TLS issuance:

```text
subject=CN = partner.cyber-vpn.net
issuer=C = US, O = Let's Encrypt, CN = E7
notBefore=May 26 07:40:04 2026 GMT
notAfter=Aug 24 07:40:03 2026 GMT
```

Operational note:

- `partner.cyber-vpn.net` was temporarily set to DNS-only to allow Caddy/Let's Encrypt origin certificate issuance, then returned to Cloudflare proxied mode.

## Edge Validation

Caddy:

```text
caddy validate --config /etc/caddy/Caddyfile -> Valid configuration
HTTP/3 listener enabled on :443
```

Public smoke:

```text
https://partner.cyber-vpn.net/healthz -> 200
https://partner.cyber-vpn.net/ru-RU/login -> 200
https://partner.cyber-vpn.net/ru-RU/dashboard -> 200
https://partner.cyber-vpn.net/ru-RU/register -> 200
https://partner.cyber-vpn.net/ru-RU/partner -> 200
https://cyber-vpn.net/ru-RU/partner -> 302 https://partner.cyber-vpn.net/ru-RU/partner
https://my.cyber-vpn.net/ru-RU/partner -> 302 https://partner.cyber-vpn.net/ru-RU/partner
```

HTTP/3/QUIC signal:

```text
alt-svc: h3=":443"; ma=86400
```

## Result

S3 partner runtime is deployed in production as a separate public surface at `partner.cyber-vpn.net`.

Next recommended check: owner login smoke in partner portal with a real partner/operator account, then confirm pilot workspace visibility, partner code attribution, reporting, and settlement sandbox from the public partner domain.
