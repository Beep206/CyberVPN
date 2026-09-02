# ADR 0003: Remnawave 3.4.1 Numeric User Identity

- Status: Accepted
- Date: 2026-08-30

## Context

Remnawave 3 removes UUID user identity from the target user-resolution and
user-route contract. The Verta HTTP adapter previously accepted a normalized
test-only response first, then retried a UUID-capable Remnawave shape after a
`400`. That behavior made schema drift indistinguishable from compatibility
negotiation and could preserve UUID as the effective canonical identity after
the control plane moved to numeric IDs.

The CyberVPN upgrade targets panel/backend/frontend `3.4.3` while preserving
the stable `target-3.4.1` numeric wire profile. Rollback still
needs the pre-cutover `2.8` route shape, but rollback must be explicit and must
not weaken the target path.

## Decision

- `target-3.4.1` is the default `HttpRemnawaveAdapter` profile.
- The target resolve request contains exactly one of numeric `id`, `shortUuid`,
  or `username`; the Verta bootstrap flow sends only `shortUuid`.
- The target resolve response is
  `{ "response": { "id", "username", "shortUuid" } }`.
- The normalized `AccountSnapshot.account_id` is the positive numeric user ID
  encoded as a decimal string. This preserves the existing private Bridge trait
  while making numeric identity canonical.
- Target account and metadata calls use `GET /api/users/{id}` and
  `/api/metadata/user/{id}`. Metadata upsert sends `{ "metadata": patch }`.
- Account-scoped verified webhook effects validate and normalize the same
  profile-specific identity before scheduling reconciliation.
- `legacy-2.8-rollback` is an explicit operator-selected profile. It keeps UUID
  routes only for rollback and never participates in automatic fallback.
- UUID-only target responses, missing/non-numeric IDs, cross-profile account
  identifiers, and malformed metadata fail closed as schema or input errors.

## Alternatives Considered

- Automatically retry the 2.8 UUID contract after a target response fails.
  Rejected because malformed or hostile target responses could silently select
  a weaker identity contract.
- Change every Bridge domain record from `String` to a new numeric type in this
  release. Rejected because the private adapter boundary already treats
  `account_id` as opaque, and a decimal representation gives the requested
  canonical identity without widening the frozen public `/v0/*` contract.
- Keep UUID returned alongside numeric ID as a target-profile fallback.
  Rejected because the 3.4.1 resolve contract no longer includes UUID and the
  upgrade requires numeric identity to be canonical.

## Consequences

- Target and rollback behavior are deterministic and operator-visible.
- Existing Bridge stores can retain their string column while receiving only
  decimal numeric account IDs from the target adapter.
- A rollback profile can read legacy UUID-owned state, but operators must use
  the documented rollback sequence; the adapter does not reconcile the two
  identity domains automatically.
- Automated fixtures prove the 3.4.1 shapes and negative drift behavior. They
  do not constitute a live upstream or production deployment pass.

## Spec Links

- `docs/spec/verta_remnawave_bridge_spec_v0_1.md` sections 5.3, 8.1, 13, 19, 20, 29, 43, and 45
- `docs/spec/verta_threat_model_v0_1.md` section 15.2 and `TM-CP-04`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md` suite `RW` and section 18

## Rollback

Select `legacy-2.8-rollback` only together with the control-plane database and
panel rollback. Do not mix target numeric account state and legacy UUID account
state in one running Bridge cohort. Returning to `target-3.4.1` requires the
normal numeric-ID reconciliation gate before traffic is promoted again.
