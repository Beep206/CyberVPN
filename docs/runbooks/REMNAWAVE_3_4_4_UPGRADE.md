# Remnawave 3.4.4 Patch Upgrade (from 3.4.3)

Use this procedure to move the CyberVPN custom panel/backend/frontend from
3.4.3 to 3.4.4. Remnawave Node stays on 3.4.1 and Subscription Page stays on
8.0.0. Everything not listed here (guardrails, backups, stream checks, evidence
record) follows `REMNAWAVE_3_4_3_UPGRADE.md` and
`REMNAWAVE_UPGRADE_GUARDRAILS.md`.

## Pinned target

| Item | Value |
| --- | --- |
| Backend tag / commit | `3.4.4` / `b22970cc88481a7e278b5767721672a18f8b2ada` |
| Frontend commit (image metadata) | `cb4453bcfa4254ef91301f9a68d727da861487fb` |
| Upstream image index | `remnawave/backend:3.4.4@sha256:63ef481550bbf49dabfa514c95d94109619cc85607730b308f7ad0b9b5599f06` |
| Compat build base | `node:24.21-trixie-slim` (matches upstream 3.4.4) |
| CyberVPN compat image tag | `cybervpn/remnawave-backend:3.4.4-raw-vision-flow.1` |
| `@remnawave/backend-contract` | `3.4.15` (was `3.4.13`) |

## Upstream delta that matters to CyberVPN

- No Prisma schema migrations between 3.4.3 and 3.4.4.
- The subscription-request Redis stream producer now emits the contract field
  `srrResponseType` (3.4.3 emitted `ssrResponseType`). The task-worker keeps
  accepting both spellings, so pending 3.4.3 entries and a panel rollback stay
  safe. The compat build now fails if the producer regresses.
- The `subscription-refill-date` response header is derived from the same
  schedule as the traffic-reset jobs: DAY +5 min, WEEK (Monday) +15 min,
  MONTH (1st) +20 min, and it is now also emitted for `MONTH_ROLLING` users
  (anchored to the user's creation day). Clients that display this header see
  slightly different timestamps; no CyberVPN code parses it.
- The default subscription response rules add the `rabbit` client to the
  Clash/Mihomo user-agent rule. Upstream only replaces the SRR config when it
  still equals the previous default hash; a customised config is untouched.
- New `POST` clone-host operation and error code `A258`; next traffic-reset
  template variables. CyberVPN does not expose either yet.
- Updating a node no longer restarts it unless a connection-relevant field
  changed; node names are trimmed. Node queue jobs are retained for 12 h / 500
  entries instead of 24 h.

## CyberVPN changes shipped with this target

- `GET /api/v1/admin/remnawave/capabilities-and-streams` and the
  customer/partner VPN service-status readiness checks require panel version
  exactly `3.4.4`; the admin endpoint reports contract `3.4.15`. Any other
  version, including `3.4.3`, fails closed (`panel_version_mismatch` for admin,
  `panel_unavailable_or_mismatched` for customer/partner).
- `scripts/deploy/stage1-gitlab-deploy.sh` accepts only a digest-pinned
  `...:3.4.4-raw-vision-flow.N@sha256:<64 hex>` panel image.
- The compat image verifies the pinned 3.4.4 source with
  `verify-upstream-3.4.4-regressions.mjs`; the RAW Vision validator patch and the
  scoped Node SSH broker apply unchanged (upstream did not touch those files).

## Procedure

1. Build the compat image through `control-plane-images` and promote it with
   the normal supply-chain evidence. Record the registry digest.
2. Take and verify the Remnawave PostgreSQL backup exactly as for 3.4.3, even
   though no schema migration is expected.
3. Deploy from this repository revision only: set
   `CYBERVPN_REMNAWAVE_BACKEND_IMAGE=...:3.4.4-raw-vision-flow.1@sha256:<digest>`
   and roll out the panel and the CyberVPN backend built from the same
   revision in one change window (panel first). The stage1 deploy gate of this
   revision accepts only a digest-pinned `3.4.4-raw-vision-flow.N` panel image,
   and the previous revision's gate accepts only `3.4.3`, so the two must not be
   mixed across pipelines. Until both are running, admin Remnawave
   capabilities and customer connections/usage readiness are intentionally
   reported as degraded.
4. Smoke checks:
   - `GET /api/system/metadata` on the private panel returns `3.4.4` and the
     frontend commit above.
   - `GET /api/v1/admin/remnawave/capabilities-and-streams` returns `target_panel_version=3.4.4`,
     `contract_version=3.4.15` and no `degraded_reason` once streams are
     observed.
   - Fetch a synthetic subscription through the public proxy and check the
     `subscription-userinfo` and `subscription-refill-date` headers.
   - New subscription-request stream entries carry `srrResponseType`; the
     `cybervpn-remnawave-v1` consumer group has no growing lag or dead letters.
   - Existing 3.4.1 nodes stay connected; editing a node's name alone does not
     restart it.

## Rollback

Re-run the deploy of the previous repository revision (the last commit that
targets 3.4.3) with its `3.4.3-raw-vision-flow.2` digest; the current
revision's deploy gate refuses 3.4.3 images by design. Panel and CyberVPN
backend roll back as a pair because of the exact-version gate. No database
restore is needed because 3.4.4 ships no schema migration, unless the
backup/restore gate was triggered for an unrelated reason.
