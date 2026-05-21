# Stage 1 Rented Prod 15D Invite Config Delivery Evidence

Date: 2026-05-21

## Scope

- Fix Mini App invite redeem state refresh without requiring a full Mini App reload.
- Fix invite-based active access without VPN config by provisioning Remnawave access during invite redemption.
- Remediate the already redeemed internal invite user with redacted production evidence.

## Changes

- Frontend Mini App Plans now invalidates:
  - `miniapp-offers`
  - `miniapp-bootstrap`
  - `miniapp-config`
  - `usage`
  - `miniapp-profile-invites`
- Backend invite redemption now attempts S1 Remnawave provisioning before returning success.
- Remnawave gateway now replaces Telegram placeholder emails such as `@telegram.local` with a deterministic `@cyber-vpn.net` address before upstream user create/update.
- Remnawave Telegram lookup now treats an empty upstream list as "user not found" instead of logging a validation-compromise error.

## Production Deployment

- Backend image: `cybervpn/cybervpn-backend:stage1-rent15d-invite-config-20260521t140206z`
- Frontend image: `cybervpn/cybervpn-frontend:stage1-rent15d-invite-config-20260521t140206z`
- Reused/retagged unchanged runtime images:
  - `cybervpn/cybervpn-admin:stage1-rent15d-invite-config-20260521t140206z`
  - `cybervpn/cybervpn-task-worker:stage1-rent15d-invite-config-20260521t140206z`
  - `cybervpn/cybervpn-telegram-bot:stage1-rent15d-invite-config-20260521t140206z`

## Production Checks

- Backend container: healthy.
- Frontend container: healthy.
- Internal backend `/health`: HTTP 200.
- Internal frontend `/ru-RU/miniapp/home`: HTTP 200.
- Public `https://cyber-vpn.net/ru-RU/miniapp/home`: HTTP 200.
- Public response includes `alt-svc: h3=":443"; ma=86400`; HTTP/3/QUIC remains enabled.
- Backend/frontend logs after deploy: no new `error`, `exception`, `traceback`, `EACCES`, invite provisioning failure, or Remnawave validation failure lines in the checked window.

## Redacted User Access Proof

For the internal invite test user:

- Local active entitlement exists.
- Remnawave UUID present: yes.
- Subscription URL present: yes.
- Generated config present: yes.
- Remnawave links count: 2.
- Client type: `vless`.

No raw subscription URL, VPN link, token, key, invite code, or user secret was written to this evidence file.

## Tests

- Frontend:
  - `npm --prefix frontend test -- --run 'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx' 'src/app/[locale]/miniapp/components/__tests__/VpnConfigCard.test.tsx'`
  - Result: 2 files passed, 8 tests passed.
  - `npm --prefix frontend run lint -- 'src/app/[locale]/miniapp/plans/page.tsx' 'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx'`
  - Result: passed.
- Backend:
  - `uv run pytest tests/unit/infrastructure/test_remnawave_user_gateway.py tests/unit/presentation/api/v1/invites/test_invites_routes.py tests/unit/presentation/api/v1/miniapp/test_routes.py -q --no-cov`
  - Result: 29 tests passed.
  - Same targeted backend test set without `--no-cov` also passed functionally, but failed the repository-wide 70% coverage gate because it was a narrow subset.
  - `uv run ruff check src/infrastructure/remnawave/user_gateway.py src/presentation/api/v1/invites/routes.py tests/unit/infrastructure/test_remnawave_user_gateway.py tests/unit/presentation/api/v1/invites/test_invites_routes.py`
  - Result: passed.

## Security Checks

- `git diff --check`: passed.
- Targeted secret scan over changed task files and this evidence file: no raw bot token, SSH key, VPN link, subscription URL, private key, or generic secret assignment found.
- Targeted static scan over changed runtime files: no `eval`, `dangerouslySetInnerHTML`, `innerHTML`, `subprocess`, `os.system`, or `shell=True` use found.
- `npm --prefix frontend audit --audit-level=high --omit=dev`: passed at high severity threshold. It still reports existing moderate advisories in transitive frontend dependencies.
- Backend pip audit was attempted via exported requirements. It reports the existing unresolved `pyjwt 2.12.1 / PYSEC-2025-183` advisory with no fix version shown in the checked output.

## Operational Notes

- Initial frontend rebuild accidentally included old local `.next-*` audit/probe artifacts in the Docker context and produced an oversized image.
- The build source was cleaned, frontend was rebuilt from a compact source tree, and Docker build cache was pruned.
- Server disk after builder prune: root filesystem around 43 GB used / 189 GB free.

## Residual Risk

- Frontend image is still larger than ideal because the current Next.js production image keeps a full standalone runtime path for many pre-rendered locale routes. This is not a launch blocker, but should be optimized later with a stricter production Dockerfile and `.dockerignore`.
