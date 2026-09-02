# Remnawave Upgrade Guardrails

This runbook defines the release boundary for the CyberVPN Remnawave 3.4 line.
It does not authorize a production deployment.

## Current target

- panel/backend/frontend: custom `3.4.3-raw-vision-flow.2`
- upstream backend base: `remnawave/backend:3.4.3@sha256:4ea85b2fc16bd3e5d367b61afc07ec219133eaa12dd7b5e898adc33c84515422`
- upstream backend commit: `f8ad8ad3410252215ca7b2e429d157bd275ec564`
- upstream frontend commit/artifact: `c2c9ba3b476e4914a3b17e8ce677ab9255e1c02f` / `sha256:947e78b5c89ee49f1ac0389b1bd3c943a4aaf90dce32ce51fb44010182613132`
- edge node: `remnawave/node:3.4.1@sha256:0cdf386dd49f360fc885bb34bde21132e478e40f0deac62d616086ec0fa9257e`
- subscription page: `remnawave/subscription-page:8.0.0@sha256:04e8d479afb3598024e4018e9e15cd7fe879938250090a690ba39f1ee91b79ac`
- data services remain PostgreSQL `17.10` and Valkey `8.1.8` over TCP

The custom backend is not promoted by its mutable local tag. Build it from
`infra/remnawave-backend-compat/`, publish it, and put its immutable registry
digest in each environment's `control_plane_release_images.remnawave` field.

## Non-negotiable ordering

1. Preserve a restorable PostgreSQL backup and the previous environment file.
2. Prove restore in an isolated staging database before touching the target.
3. Upgrade the custom panel/backend/frontend to `3.4.3` while nodes remain on
   the old version. A 3.3+ node must never connect to a panel below 3.3.
4. Run API, subscription, webhook, worker, partner, admin, and node inventory
   smoke checks.
5. Upgrade one node to `3.4.1`, observe it, then continue one region at a time.
6. Upgrade subscription page `8.0.0` and check `/internal/health` plus an actual
   subscription render through the public reverse proxy.

Do not reverse this order. Panel 3.4.3 supports older nodes during the canary;
node 3.4.1 relies on the 3.x panel-node contract.

## Secret and environment migration

- Replace `JWT_AUTH_SECRET` with `APP_SECRET`, preserving the exact existing
  value. Do not rotate it in the upgrade window.
- Remove `JWT_API_TOKENS_SECRET`, `SWAGGER_PATH`, `SCALAR_PATH`, and
  `IS_DOCS_ENABLED`; they are not 3.x configuration.
- Keep `SHORT_UUID_METHOD=nanoid` and `SHORT_UUID_LENGTH=16` unless a reviewed
  product requirement chooses another method. A custom pattern must produce
  16–64 characters and at least about 64 bits of randomness.
- `EXPORT_TO_STREAM_MAXLEN=3000` is the bounded default. Enable
  `EXPORT_TO_STREAM_ENABLED=true` only when the version-aware consumers and
  lag/trim monitoring are deployed in the same release.
- CyberVPN's backend consumer must ship in that same release with
  `REMNAWAVE_STREAM_INGESTION_ENABLED=true` and consumer group
  `cybervpn-remnawave-v1`. Configure a dedicated random
  `REMNAWAVE_STREAM_IP_HMAC_SECRET` of at least 32 characters. It must not be a
  placeholder and must be pairwise distinct from `APP_SECRET`, JWT,
  Remnawave/webhook, Telegram, payment/provider, internal-service and Node SSH
  broker credentials. On the worker this also includes metrics Basic Auth,
  Resend, Brevo and SMTP secrets plus the parsed passwords from `DATABASE_URL`,
  `REDIS_URL` and `REMNAWAVE_STREAM_REDIS_URL`; compare the decoded password,
  never the whole URL. The backend and worker settings validators both fail
  closed on secret reuse while stream ingestion is enabled.
- Configure `WEBHOOK_LOG_FINGERPRINT_SECRET` as an independent random value of
  at least 32 characters. It domain-separates HMAC-SHA256 fingerprints used in
  retained webhook metadata and application logs. It must differ from auth,
  provider, DSN-password, `APP_SECRET`, Node SSH, and stream keys. If it is
  absent, the backend intentionally omits fingerprints; there is no SHA-256 or
  cross-domain-secret fallback. This also disables stored-body fingerprint
  duplicate lookup; timestamp/signature validation remains enforced, but the
  production deployment gate therefore requires the key. Rotate it only with
  an explicit loss-of-log-correlation decision, because new and old
  fingerprints will not match.
- The task worker must receive `REMNAWAVE_STREAM_REDIS_URL` explicitly. In the
  stage stack it is `redis://cybervpn-remnawave-valkey:6379/0`, while
  `REDIS_URL=redis://cybervpn-valkey:6379/0` remains the independent Taskiq and
  cache transport. The worker must join `cybervpn-remnawave-data`; never fall
  back from the stream URL to `REDIS_URL`. Keep the scheduler's stream consumer
  disabled so only worker replicas participate in the consumer group.
- Keep `REMNAWAVE_STREAM_RECEIPT_MAX_IDLE_SECONDS=300` for this release. The
  backend validates a 30-3600 second range and marks a committed receipt stale
  at the exact max-idle boundary. Stale or missing receipts fail closed, and
  `redis_stream_export` remains unavailable until lag and pending depth are
  both observed within the release readiness thresholds.
- Keep stream receipt/user-usage/subscription-request/node-connection
  retention at `14/180/30/30` days respectively for this release. A retention
  change is a separately reviewed data-lifecycle change. The worker value
  `REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS=14` must match the backend; a
  reclaimed PEL entry at or beyond that age is registered as a gap and REST
  reconciled before `XACK`, never replayed into additive projections.
- Keep Valkey on TCP (`REDIS_HOST` and `REDIS_PORT`); do not silently switch the
  current topology to a Unix socket during this upgrade.

For node 3.4.1, all three values must be explicit:

```text
SNI_VERIFICATION=true
NFTABLES_LOGGING=true
NFTABLES_ACCEPT_REPLY_TRAFFIC=false
```

`SNI_VERIFICATION=true` preserves CyberVPN's required SNI protection. Prove
the configured Reality/Xray SNI set in staging before the node canary. Any
legitimate-client handshake rejection, SNI mismatch, panel disconnect, or
unexpected Xray restart is a stop condition: do not turn verification off as
a rollout workaround. Changing `NFTABLES_ACCEPT_REPLY_TRAFFIC` also changes
filtering semantics and requires an isolated canary.

The native Remnawave panel is not a public application surface. Stage Compose
publishes ports 3000/3001 only on `127.0.0.1` (host ports 13005/13006), the
Ansible control-plane role rejects a non-loopback panel bind, and the public
Caddy routes do not proxy port 13005. Operator access must stay behind the
approved VPN/SSO/IP allowlist. Missing or bypassable access control, a direct
public socket, or a new public reverse-proxy route is a release stop condition.

## RAW Vision compatibility build

The custom backend must never patch a file already compiled inside the image.
The Docker build must:

1. clone tag `3.4.3`, require commit `f8ad8ad3…`, and fail the build unless the
   exact source preserves the mixed-case `backend-tools` authentication guard
   plus the inherited HWID-concurrency and nullable-OpenAPI fixes;
2. apply the fail-closed patch to
   `src/common/helpers/xray-config/xray-config.validator.ts`;
3. require numeric `user.id`, remove inbound-level `settings.flow`, and add
   non-empty Vision flow to each VLESS client;
4. run the upstream formatter against the patched source, the full upstream
   linter, Prisma generation, and the complete backend build;
5. verify the official base image metadata identifies the same version and
   commit before replacing the complete backend bundle.

Any source-pattern, user-id mapping, commit, version, or base-image drift must
fail the image build. Never weaken these checks to make a later upstream tag
build; review and version the patch instead.

The upstream 3.4.3 tag has unrelated formatter drift in untouched files
under its locked `oxfmt`. For that reason the build runs formatting against
the only file CyberVPN changes and runs `oxlint` across the complete source
tree. Do not replace the targeted formatter gate with a formatter write pass;
that would silently rewrite upstream source in the release image.

## Database and rollback boundary

The 2.8→3.x migration removes user UUIDs, deletes invalid HWID rows, drops
legacy columns/tables, and has no supported automatic down migration. Before
promotion, record counts and restore evidence for at least:

- users and their numeric IDs/short UUIDs;
- invalid HWID rows selected by the upstream migration;
- external squad and subscription response-header data;
- node inventory, profiles, hosts, and API tokens.

Panel rollback after migrations is **database restore plus old image and old
environment**, not an image-only rollback. Node rollback can use the previous
release symlink only while the panel has not assigned 3.4-only integrations or
plugins to that node.

The CyberVPN webhook-log cleanup is intentionally privacy-irreversible: it
removes v1 plain-SHA identifier/signature fingerprints because the raw source
values are not retained and therefore cannot be re-HMACed. Its Alembic
downgrade is a safe no-op. The prior backend accepts the remaining allowlisted
metadata without fingerprint fields, so an application rollback stays
operational without resurrecting enumerable identifiers.

On a rehearsed downgrade/re-upgrade, the cleanup runs again and deliberately
removes any existing v2 HMAC fingerprint fields as well: the migration cannot
prove which key produced an arbitrary persisted value. This privacy-safe loss
temporarily resets log correlation and Remnawave body-deduplication history;
new v2 events rebuild both under the currently configured dedicated key.

Drain this backlog before starting Alembic. First run the read-only snapshot,
then pass its exact fingerprint to the apply command:

```bash
cd backend
python scripts/cleanup_legacy_webhook_fingerprints.py
python scripts/cleanup_legacy_webhook_fingerprints.py \
  --apply --expected-fingerprint '<fingerprint-from-dry-run>'
python scripts/cleanup_legacy_webhook_fingerprints.py
```

The apply command locks and commits at most 500 rows per transaction and is
safe to resume after interruption by taking a new dry-run fingerprint. It
prints counts and fingerprints only, never identifiers or payloads. The final
dry run must report `ready_for_alembic: true`. The migration itself refuses to
update more than 5,000 residual candidates inside Alembic's single revision
transaction; that refusal is a stop condition, not a gate to override.

## Required local validation

Run from the repository root:

```bash
node --test infra/remnawave-backend-compat/test/*.test.mjs
python -m pytest -q infra/tests/test_remnawave_3_4_infra.py infra/ansible/tests/test_control_plane_phase8.py
docker compose --env-file infra/.env.example -f infra/docker-compose.yml config --no-env-resolution --quiet
REMNAWAVE_STREAM_IP_HMAC_SECRET=compose-validation-only-not-for-deploy-0001 \
WEBHOOK_LOG_FINGERPRINT_SECRET=compose-validation-only-not-for-deploy-0002 \
CYBERVPN_NODE_SSH_PROXY_IMAGE=ghcr.io/example/render-only@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  docker compose --env-file infra/deploy/stage1/remnawave-panel.env.example \
  -f infra/deploy/stage1/docker-compose.stage1.yml \
  config --no-env-resolution --quiet
```

The inline value above exists only to exercise Compose's required-variable
path. It must never be copied into a deployment secret source; Ansible rejects
it as a placeholder.

Also build the custom image with network access. Its source check and upstream
build are release gates, not optional diagnostics:

```bash
docker build --pull \
  --tag cybervpn/remnawave-backend:3.4.3-raw-vision-flow.2 \
  infra/remnawave-backend-compat
```

Run Ansible syntax checks and `remnawave-verify.yml` against staging inventory.
No production host is a validation target for this change.

### Cross-surface contract gates

The canonical 3.4 response models live in
`backend/src/infrastructure/remnawave/contracts.py`. Webhook compatibility must
continue to verify `REMNAWAVE_WEBHOOK_SECRET`, `X-Remnawave-Signature`, and
`X-Remnawave-Timestamp`; Node Plugins remain an explicit privileged operator
boundary. Regenerate and compare every API consumer with
`scripts/check-generated-artifacts.sh`.

Run the worker and Rust compatibility checks as explicit release gates:

```bash
cd services/task-worker
python -m pytest tests/unit/test_remnawave_normalizers.py tests/test_services.py

cd ../../services/helix-adapter
cargo test node_registry_inventory_helper_accepts_current_remnawave_fixture
cargo clippy --all-targets -- -D warnings
```

### Bulk mutation safety boundary

Admin/API and task-worker bulk enable/disable operations are fail-closed in
this release. They perform no provider I/O and return an explicit unavailable
result until durable per-user attempt receipts, exact postcondition
reconciliation, and partial-outcome reporting are implemented. This prevents
an identity mismatch or ambiguous timeout from being converted into HTTP 200
with an empty success list, or from being replayed by an at-least-once queue.

Admin customer VPN credential regeneration is also fail-closed with HTTP 503.
Remnawave has no idempotency key, and `revokeOnlyPasswords` exposes no safe
readback that proves whether a lost-response rotation was accepted. Do not
enable that button or endpoint until the target-scoped durable attempt receipt,
operator settlement path, and replay response contract are implemented and
tested. Single-user update/delete/full-revoke transport ambiguity is reconciled
only by a safe exact-identity GET and never by replaying the mutation.

## Exit criteria

- custom panel image is published and promoted by digest;
- pre-upgrade backup and isolated restore evidence exist;
- migrations pass against populated staging data;
- panel is healthy at metrics-port `/health`;
- all three versioned Redis streams are consumed by `cybervpn-remnawave-v1`, with
  bounded lag and no dead-letter/receipt replay storm;
- subscription page is healthy at `/internal/health` and renders a real test
  subscription;
- old nodes reconnect to panel 3.4.3 before the node canary begins;
- the node canary passes client compatibility, Xray config, metrics, nftables,
  GeoCheck, and rollback checks;
- every API consumer has passed its 3.x contract tests;
- PostgreSQL-backed concurrent HWID registration proves one row/one added event
  without duplicate-key failures, and provider OpenAPI has no array-valued
  nullable `type`;
- node 3.4.1 credential rotation drops only the old credential's captured user
  connections and leaves unrelated users connected;
- no production rollout begins without explicit authorization.
