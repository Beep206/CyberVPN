# Remnawave 3.4.3 Upgrade Procedure

Use this procedure for the controlled migration from the CyberVPN custom 2.8.0
panel to custom panel/backend/frontend 3.4.3, Remnawave Node 3.4.1, and
Subscription Page 8.0.0. Complete the guardrails in
`REMNAWAVE_UPGRADE_GUARDRAILS.md` first.

The 3.4.3 patch scope is intentionally narrow: backend commit
`1581086be26570e19536fa9a3a2017630e25c9e4` closes mixed-case
`backend-tools` authentication bypasses, while frontend commit
`ef75c5394d59ec64e6aa118c8c1a35fe5012f3c9` supplies stable item keys for
virtualized records. Node remains 3.4.1 and Subscription Page remains 8.0.0.
Do not combine this patch transition with unrelated runtime or data changes.

## 0. Validate the pre-upgrade baseline

Before building or promoting anything, collect one sanitized, read-only
inventory from staging and one from production (see
`scripts/remnawave/baseline-inventory.example.json`) and validate them against
the three approved pre-upgrade image digests:

```bash
python scripts/remnawave/validate-upgrade-baseline.py \
  --inventory <sanitized-staging-inventory.json> \
  --inventory <sanitized-production-inventory.json> \
  --expected-panel-digest sha256:<approved-panel-64-hex> \
  --expected-node-digest sha256:<approved-node-64-hex> \
  --expected-subscription-digest sha256:<approved-subscription-64-hex> \
  --expected-staging-binding-sha256 <approved-staging-binding-64-hex> \
  --expected-production-binding-sha256 <approved-production-binding-64-hex> \
  --expected-staging-node <approved-sanitized-staging-node-name> \
  --expected-production-node <approved-sanitized-production-node-name> \
  --max-age-minutes 60
```

Repeat the relevant `--expected-staging-node` or
`--expected-production-node` argument once for every approved node. The
expected environment-binding fingerprints and node lists come from the
separately approved deployment inventory; do not copy them from the snapshot
being validated. They contain no secret values.

Schema version 2 is strict and fail-closed. Each snapshot must be no older than
the configured window (60 minutes by default and never more than 360 minutes),
no more than five minutes in the future, and the staging/production collection
times must be within 30 minutes of each other. The validator recomputes the
node count and SHA-256 of the compact JSON array of sorted node names. It also
requires matching counts, sorted-ID-set fingerprints, and affirmative parity
for users, mappings, nodes, hosts, profiles, squads, plugins and HWIDs, plus
matching Remnawave migration counts and migration-set fingerprints. Unknown or
missing schema fields are rejected so a typo cannot silently weaken evidence.
For each `state_parity` group, `authoritative_*` is produced by an independent
read from the owning datastore and `observed_*` by the complete paginated
API/export path that will feed reconciliation, against the same read boundary.
Hash the UTF-8 compact JSON array of sorted normalized IDs; retain only the
aggregate count and SHA-256 fingerprint, never the raw ID set.

Use approved inventory evidence and digests only; never place secret values in
either inventory. Exit code `2`, stale evidence, an environment/topology,
version/digest/migration/parity mismatch, a missing environment, or a
non-sanitized/non-read-only inventory is a hard stop.

## 1. Freeze the candidate

1. Build `infra/remnawave-backend-compat/` from a clean reviewed commit.
2. Run `.github/workflows/control-plane-images.yml` from the protected default
   branch. It must build all seven CyberVPN release images, fail on any high or
   critical Trivy result, and sign SLSA provenance, SPDX SBOM, and the scan
   predicate for each exact digest.
3. Run `.github/workflows/control-plane-promote.yml` with the seven digests, exact
   40-character source commit and build-run URL. The workflow verifies the
   fixed signer workflow, source ref/digest and all three attestations, then
   uploads a read-only release/evidence artifact. It has no write token and
   does not update inventory or deploy anything.
4. For a controller-side rehearsal, generate the same manifest from the verified
   evidence artifact. This is not an offline bypass: the helper performs live
   GitHub attestation verification for every digest before rendering:

```bash
cd infra
make control-plane-release-staging \
  REMNAWAVE_IMAGE=ghcr.io/<owner>/<repo>/remnawave-backend@sha256:<digest> \
  REMNAWAVE_AUTH_SECRET_SHA256=<sha256-from-sanitized-baseline> \
  BACKEND_IMAGE=ghcr.io/<owner>/<repo>/backend@sha256:<digest> \
  WORKER_IMAGE=ghcr.io/<owner>/<repo>/task-worker@sha256:<digest> \
  HELIX_ADAPTER_IMAGE=ghcr.io/<owner>/<repo>/helix-adapter@sha256:<digest> \
  NODE_IMAGE=ghcr.io/<owner>/<repo>/remnawave-node@sha256:<digest> \
  SUBSCRIPTION_PAGE_IMAGE=ghcr.io/<owner>/<repo>/remnawave-subscription-page@sha256:<digest> \
  NODE_SSH_PROXY_IMAGE=ghcr.io/<owner>/<repo>/node-ssh-proxy@sha256:<digest> \
  SOURCE_COMMIT=<40-character-git-commit> \
  SOURCE_RUN_URL=https://github.com/<owner>/<repo>/actions/runs/<id> \
  EVIDENCE_MANIFEST=<downloaded-supply-chain-evidence.json> \
  SIGNER_WORKFLOW=github.com/Beep206/CyberVPN/.github/workflows/control-plane-images.yml
```

Do not substitute a tag for any manifest digest. Production promotion remains
blocked until the uploaded artifact is independently reviewed and the separate
deployment approval is granted.

The repository owner accepted the recorded local Docker Scout Critical/High
quickview counts as diagnostic, non-blocking risk for this task. This exception
does not erase the counts, create a signed scan attestation, or waive the
protected promotion workflow's independent Trivy/signature/SBOM/provenance
requirements. The exact local panel 3.4.3, node 3.4.1 and subscription-page
8.0.0 images now have SHA-bound unsigned SPDX documents under
`docs/evidence/remnawave-3.4.3/`; they are diagnostic only and do not replace a
registry-bound SBOM attestation, signature, or provenance. Exact current-image
Scout summaries are stored in the same evidence manifest. Historical counts remain in
`docs/evidence/remnawave-3.4.2/local-image-build-verification.json`.

## 2. Prepare data and secrets

1. Stop writes or establish the approved maintenance boundary.
2. Capture a PostgreSQL custom-format backup and configuration snapshot.
3. Restore the backup into an isolated staging database and verify row counts.
4. Copy the old `JWT_AUTH_SECRET` value exactly into the new `APP_SECRET`
   secret. Remove the obsolete token secret and docs-path variables.
5. Generate a dedicated random `REMNAWAVE_STREAM_IP_HMAC_SECRET` of at least
   32 characters. Store it only in the approved secret source, verify it differs
   from every backend/worker/panel credential, and leave checked-in examples
   empty.
6. Generate a separate random `REMNAWAVE_CONNECTION_DROP_HMAC_SECRET` of at
   least 32 characters. It must differ from authentication, provider, stream,
   database and broker secrets. Keep this value stable while any
   `outcome_unknown` receipt exists: the registry deliberately fails closed if
   another key identifier appears while active receipts remain. Configure the
   reviewed terminal TTL and the global/per-actor capacity limits; never remove
   an ambiguous receipt merely to free capacity.
7. Keep browser SSH disabled until a separate 128-lowercase-hex broker secret,
   passkey step-up, exact trusted-admin/node UUID allowlists, and the private
   REST/WebSocket proxy are configured. The proxy has no host port, overwrites
   the canonical source header, discards sensitive access logs, and is the only
   TCP peer trusted by the scoped Remnawave broker. The custom `.2` panel image
   does not register the native Node SSH controller, returns `404` from
   `/api/node-ssh/ws` before native credentials are parsed, and never selects
   the native `rw` subprotocol; an upstream ADMIN JWT is not an SSH fallback.
8. Configure the backend stream consumer with ingestion enabled, consumer group
   `cybervpn-remnawave-v1`, and receipt/user-usage/subscription-request/node-
   connection retention of `14/180/30/30` days.
9. Point the task worker's dedicated `REMNAWAVE_STREAM_REDIS_URL` at the
   Remnawave export Valkey. In stage this is
   `redis://cybervpn-remnawave-valkey:6379/0`; keep the independent Taskiq/cache
   `REDIS_URL=redis://cybervpn-valkey:6379/0`, and keep the scheduler consumer
   disabled. Supply the same dedicated `REMNAWAVE_STREAM_IP_HMAC_SECRET` to
   backend and worker; it must be at least 32 bytes and remain distinct from
   service-auth credentials. Verify that Redis DLQ entries at or beyond 14 days
   are removed and that only HMAC fingerprints reach PostgreSQL/Redis metadata.
   Enable `REMNAWAVE_STREAM_RETENTION_ENABLED=true`; the daily worker must call
   the bounded backend purge until `has_more=false` or the configured batch cap,
   and the backlog metric must remain zero after the soak.
10. Confirm PostgreSQL remains 17.10 and Valkey remains 8.1.8 over TCP.
11. Never enable `GIFT_CODES_ENABLED` while
    `STAGE1_PAID_PROVISIONING_ENABLED` is false. The backend now rejects that
    configuration at startup and both gift redemption entrypoints fail before
    consuming a one-use code when the provider gateway is unavailable. Staging
    must additionally prove the gift-global ambiguity latch and concurrent
    two-customer redemption: at most one provider call, grant and redemption
    may survive.

Never run the migration against production before the restore drill and
populated staging migration succeed.

## 3. Upgrade the panel first

1. Keep every edge node on its current image.
2. Deploy the digest-pinned custom panel/backend/frontend 3.4.3 candidate to
   staging. Allow its normal entrypoint to run the upstream migrations.
3. Require scheduler health at `http://127.0.0.1:3001/health`.
4. Check authentication, numeric user IDs, API tokens/scopes, user CRUD,
   webhooks, subscriptions, squads, hosts, profiles, node inventory, and stream
   consumers.
   - Against the running candidate, request the canonical and at least one
     mixed-case `backend-tools` path without credentials. Both requests must
     be denied by the same authentication boundary before any tool handler
     response is returned; valid authenticated access must remain functional.
     Any bypass, status/body divergence that exposes handler behavior, or
     sensitive response is a stop condition.
   - In the private native panel, scroll, filter and reorder a virtualized
     record list and require stable row identity with no duplicated or
     substituted record. This is a target artifact smoke, not a new CyberVPN
     Admin, Partner or Customer capability.
   - For an existing active subscription, onboarding/current-state must reuse
     the one exact customer/realm/provider/numeric service identity and update
     only its active subscription delivery channels. A stale UUID-only account
     identity, duplicate mapping, pagination overflow, or mismatched ledger is
     a `409` stop condition; no provider create may occur and no raw old/new
     subscription URL may enter logs or audit.
   - Verify MiniApp/customer readiness from the canonical selected service
     identity and channel. A legacy-only `mobile_user.subscription_url` must
     leave `hasConfig=false`; a canonical active channel must restore readiness.
   - Exercise the public short-token gateway with four negative fixtures:
     provider-only identity and exact mapped identity without an active grant
     return `404`; multiple active candidates, pending/conflicting ledger state,
     or provider/local numeric/UUID mismatch return `503`. Every rejected path
     must perform zero subscription-proxy calls and zero provider mutations.
5. Run the 3.4.3 HWID concurrency gate against PostgreSQL: concurrent requests
   for the same user/device must create one row, return only deterministic
   created/existing outcomes, publish one added event, and never return a
   duplicate-key 500. Concurrent distinct devices must not exceed the device
   limit, while an already registered device remains accepted at the limit.
6. Export the tagged provider OpenAPI and require nullable schemas to use
   `anyOf`; any array-valued `type` is a stop condition. Regenerate CyberVPN's
   frontend, Admin and Partner clients twice and require the second generation
   to have no diff.
7. Verify the backend consumes all three versioned Redis streams under group
   `cybervpn-remnawave-v1`; inspect lag, receipt expiry, replay/idempotency, and
   HMAC-redacted IP handling without exposing the HMAC secret in logs.
8. Inspect `remnawave_connection_drop_receipts`. A newly reserved mutation must
   be committed as `outcome_unknown` with `expires_at IS NULL` before provider
   I/O. Replay must return that same receipt without another provider call and
   report `requires_reconciliation=true` with no expiry. Only an acknowledged
   `accepted` or definitive `rejected` receipt receives the configured terminal
   TTL and becomes purgeable after that deadline. Verify expired terminal-key
   reuse, bounded cleanup, the global active-row limit, the unresolved-per-actor
   limit and fail-closed HMAC-key rotation. Alert on unresolved count, capacity
   rejections and table/index growth; reconciliation, not deletion, resolves an
   ambiguous receipt.
9. Reconcile an ambiguous receipt only through the admin API, never with SQL or
   by deleting the row. A global `admin` (or stronger) role first lists
   `GET /api/v1/admin/remnawave/connections/drop-receipts/unresolved`, then
   loads the exact 43-character opaque receipt ID, obtains independent provider
   support or postcondition evidence, and posts only `outcome`, the matching
   bounded reason enum, and an approved opaque `CASE-/INC-/REQ-/TKT-/RW-`
   reference to
   `POST /api/v1/admin/remnawave/connections/drop-receipts/{receipt_id}/reconcile`.
   Do not paste an idempotency key, HMAC, scope, IP, provider response, secret,
   or free text. Cookie sessions require the approved admin Origin/Referer;
   server-authorized bearer callers remain subject to admin-realm authorization.
   An exact repeat is idempotent and must keep one
   `remnawave.connections.drop.reconciled` audit event; a different terminal
   decision/reference returns `409` and the first committed decision remains
   immutable. Audit failure must leave the receipt `outcome_unknown`. The
   terminal TTL begins at the server reconciliation timestamp. Reconciliation
   by receipt ID remains available during HMAC-secret recovery, but rotation is
   still blocked until every unknown receipt is resolved and every receipt made
   terminal under the old key has expired.
10. Confirm existing old-version nodes reconnect and continue serving traffic.

If this step fails after migrations begin, restore the database and previous
environment before restarting the 2.8 image.

## 4. Upgrade the subscription page

1. Deploy the pinned 8.0.0 digest.
2. Require `GET /internal/health` to return 200 inside the container.
3. Fetch a synthetic user's subscription through the public proxy and verify
   headers, status, client links, and no token leakage in logs.

The root page is not a health probe in 8.0.0.

## 5. Canary Remnawave Node 3.4.1

1. Select one staging node. From separate read-only reads, calculate SHA-256
   of the deployed `SECRET_KEY` and of the matching panel node payload; record
   only the two fingerprints in the sanitized baseline and require equality.
   Put the same lowercase fingerprint in the encrypted Ansible vault metadata.
   The role rejects placeholders, malformed/short certificate payloads, and
   any secret whose digest differs from the pre-upgrade baseline.
2. Render its env with `SNI_VERIFICATION=true`, the explicit nftables flags,
   and the pinned 3.4.1 digest.
3. Deploy through the normal Ansible canary path.
4. Verify panel connection, Xray configuration, RAW Vision client-level flow,
   GeoCheck, metrics, nftables, restart behavior, and logs.
5. Rotate one synthetic user's VLESS UUID. Require node 3.4.1 to capture only
   that user's IPs before removing the old credential, emit exactly one scoped
   connection-drop event, then install the new credential. A normal create and
   an IP lookup failure must never trigger a broad drop; an unrelated user's
   connection must remain intact.
6. Before exercising clients, run the redacted inbound diagnostic and require
   exact `minClientVer=26.3.27` on every base/DE/MSK RAW and XHTTP Reality
   inbound. The seed and runtime tester fail closed on a missing or stale
   value, but they do not mutate panel-owned profiles. Then exercise every
   supported CyberVPN client family: Reality minimum-version behavior can
   reject older Mihomo, Sing-box, or Xray clients.
7. Observe for the approved window before continuing one region at a time.

Keep browser Node SSH disabled by default. A separately approved enablement
must set both passkey flags and non-empty canonical UUID allowlists in
`REMNAWAVE_NODE_SSH_TRUSTED_ADMIN_IDS` and
`REMNAWAVE_NODE_SSH_ALLOWED_NODE_IDS`; an empty or malformed list is a stop.
Only the CyberVPN broker path may be enabled; restoring native Remnawave SSH
requires an explicit image rollback/rebuild and is not an operational toggle.

Stop the rollout on any legitimate-client SNI rejection, SNI mismatch, panel
disconnect, unexpected Xray restart, nftables regression, or failed rollback
probe. Do not disable SNI verification to make the canary pass, and do not
upgrade all nodes in parallel.

Before panel promotion, confirm ports 3000/3001 are loopback-only and the
native panel has no public Caddy route. Operator access must use the approved
VPN/SSO/IP allowlist; a direct public panel route is a stop condition.

## 6. Rollback

### Panel

1. Stop the failed 3.4.3 panel.
2. Restore the pre-upgrade PostgreSQL backup into the explicitly selected
   target database.
3. Restore the previous environment, including its old variable names.
4. Start the previous digest-pinned custom image.
5. Verify API, subscriptions, and old nodes before reopening writes.

The `20260831_drop_receipts` downgrade is intentionally expand-only: it reverts
the partner grant constraint/index but retains the exact
`remnawave_connection_drop_receipts` table, all `outcome_unknown` tombstones,
and all unexpired terminal replay receipts. Re-upgrade validates the retained
columns, checks, foreign keys, unique constraints, and indexes before any grant
DDL and fails closed on a mismatch. Do not drop or recreate this table during a
code-only rollback. A rollback below the referenced admin/partner tables, or a
complete return to the pre-upgrade schema, is supported only by restoring the
verified pre-upgrade database backup as required in step 2; the restore must be
followed by a no-provider-call replay check for every retained test key.

### Node

Use the Ansible previous-release symlink only if the panel has not assigned
3.4-only node integration/plugin configuration. Re-run node and client smokes
after rollback.

### Subscription page

Restore the previous digest and its compatible environment, then verify both
its version-specific health path and a real subscription render.

## Evidence record

Keep sanitized evidence for:

- candidate and previous image digests;
- source commit and compat patch version;
- DB backup checksum, restore drill, migration transcript, and row counts;
- rendered release manifest with no secrets;
- stream consumer group, retention, lag, replay/idempotency, and redacted-IP
  evidence (never the HMAC secret itself);
- panel, subscription page, node, API consumer, and client smoke results;
- concurrent HWID row/event/result evidence and nullable OpenAPI drift result;
- scoped old-VLESS credential-drop evidence with an unrelated-user control;
- canary observation window;
- rollback command/result or rehearsed rollback proof.
