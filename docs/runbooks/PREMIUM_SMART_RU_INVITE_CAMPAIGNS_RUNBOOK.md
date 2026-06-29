# Premium Smart RU Invite Campaigns Runbook

This runbook covers the v7 flexible invite campaign flow for `premium_smart_ru`.

## Preconditions

- `premium_smart_ru` subscription plans exist for the intended duration.
- The plan is active, hidden from public catalog, and available to admin-only flows.
- Production has these Remnawave settings:
  - `REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID`
  - `REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID`
  - `REMNAWAVE_SMART_RU_PLAN_CODES=premium_smart_ru`
  - `REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME=CyberVPN Premium Smart RU`
- Admin account has 2FA enabled and permission to manage growth code sets.
- Raw export requires `growth.code_sets.export`.

## Create Campaign

1. Open Admin -> Growth -> Invite Codes -> Campaigns.
2. Create a campaign with:
   - campaign key: `premium_smart_ru_invite_wave_1`
   - grant plan: `premium_smart_ru`
   - grant duration: `365`
   - child invite count: `10`
   - child grant plan: `premium_smart_ru`
   - child grant duration: `365`
   - child expiry: `30`
   - max generation depth: `5`
   - allowed surfaces: web, miniapp, telegram bot
3. Leave publish disabled for first draft creation.
4. Validate the current version before publishing.
5. Publish only when validation passes without errors.

## Create Root Batch

1. Open Create Batch.
2. Select the campaign.
3. Set root owner user ID.
4. Set count and expiry.
5. Provide an operator reason.
6. Submit once. Raw codes are returned only for the creation response.
7. Store exported code files in the approved operator vault, not in git, tickets, logs, or chat.

## Export Root Codes

1. Open Exports & Audit.
2. Select the batch.
3. Run export with an admin that has `growth.code_sets.export`.
4. Export returns only non-used, non-revoked, non-expired raw codes.
5. Confirm the admin audit event exists for the export action.
6. Do not use generic inventory endpoints for raw codes; they intentionally return only safe prefixes and hashes.

## Inspect Tree

1. Open Invite Tree.
2. Select a root tree from the campaign root list or paste a root invite code ID.
3. Check:
   - root invite ID;
   - total nodes;
   - redeemed nodes;
   - child invites issued;
   - max depth reached;
   - granted plan code per redemption edge.
4. For a user-specific investigation, use `/admin/invite-trees/users/{user_id}` from API tooling.

## Revoke, Extend, Resend

1. Open Batches.
2. Enter a short reason before lifecycle actions.
3. Revoke unused codes when a distribution batch is compromised.
4. Extend expiry only when the campaign remains active and approved.
5. Resend notification only for approved operator communication.
6. For abuse reversals, revoke unused child invites first, then follow entitlement reversal runbooks if access was already activated.

## Verify Remnawave Smart RU Provisioning

1. Register a fresh test customer.
2. Complete OTP.
3. Apply a campaign invite code during onboarding.
4. Confirm onboarding response shows:
   - `code_type=invite`;
   - `plan_code=premium_smart_ru`;
   - `next_destination=/onboarding/connect`;
   - child invite count equals campaign policy.
5. Open connection bootstrap and verify a subscription URL is returned.
6. Confirm Remnawave user is attached to Smart RU external/internal squads and uses the Premium Smart RU subscription template.
7. Confirm `/rewards/invites` shows the child batch grouped by batch.

## Cabinet/RSC Smoke

Run after deploy:

```bash
HOST=https://my.cyber-vpn.net LOCALE=en-EN bash scripts/smoke/customer_site_rsc_routes.sh
```

The smoke sends Next.js RSC-style headers to cabinet routes and must not return
any `30x` response. A response with `Location: https://cyber-vpn.net/...` is a
release blocker because browsers reject the redirected RSC preflight as CORS.

Focused manual probe for one route:

```bash
curl -fsSI \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component' \
  -H 'Next-Router-State-Tree: []' \
  'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=smoke'
```

Also check:

- `https://my.cyber-vpn.net/en-EN/rewards`
- `https://my.cyber-vpn.net/en-EN/rewards/invites`
- `https://my.cyber-vpn.net/en-EN/rewards/gifts`
- `https://my.cyber-vpn.net/en-EN/rewards/codes`
- `https://my.cyber-vpn.net/en-EN/rewards/notifications`
- `https://my.cyber-vpn.net/en-EN/messages`
- `https://my.cyber-vpn.net/en-EN/onboarding/code`

## Mini App Session-First Auth

1. Open a protected Mini App route from Telegram with an existing valid
   customer session.
2. Confirm the frontend calls `/api/v1/auth/session` before spending
   Telegram `initData`.
3. If `/api/v1/auth/session` restores the customer, the route must continue
   without a browser-login fallback and without submitting initData again.
4. If initData is missing or expired, the UI must show Telegram-only recovery
   actions: retry, open bot, or close Mini App.
5. If backend returns `TELEGRAM_INIT_DATA_REPLAYED`, the frontend should retry
   session restore. If restore still fails, keep the user in the Mini App
   recovery state rather than redirecting to browser login.

## Admin Inventory and Surfaces

1. Open Admin -> Growth -> Invite Codes -> Campaigns.
2. Confirm at least one allowed surface is selected before submit. Submitting
   with all surfaces cleared must be blocked client-side.
3. Campaign cards and settings must show the allowed surfaces snapshot.
4. Open Inventory and confirm the admin API response is the paginated envelope:
   `{items,total,offset,limit}`.
5. Confirm inventory rows expose only safe fields: prefixes, hashes,
   campaign/batch/owner/plan metadata, child policy preview, usage state, and
   expiry. Raw invite codes must not appear in inventory.
6. Change rows per page and page navigation. The visible range and backend
   `offset`/`limit` must move together.

## Legacy Manual Premium Smart Guard

Manual `/admin/invites` creation for `premium_smart_ru` must be treated as a
legacy escape hatch only:

1. A request with `plan_id` for `premium_smart_ru` and no
   `legacy_acknowledgement=true` must return `422` with code
   `PREMIUM_SMART_REQUIRES_FLEXIBLE_CAMPAIGN`.
2. A request with `legacy_acknowledgement=true` may proceed only through the
   existing admin-authenticated route.
3. Successful legacy creation must emit `invite.legacy_manual_created` audit
   and outbox records without raw invite codes in payloads or logs.

## Rollback

1. Pause the campaign.
2. Revoke unredeemed root or child batches if distribution must stop immediately.
3. Keep redemption ledger and invite tree rows; do not hard-delete production records.
4. Roll back application deployment only after confirming migration downgrade
   safety in the release runbook.
5. After rollback, rerun the Cabinet/RSC smoke before reopening Mini App or
   invite onboarding traffic.
