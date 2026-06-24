# Partner Attribution Migration Preflight

Task: `PARTNER-ATTRIBUTION-HARDENING`

Current head: `20260622_partner_owner_ranges`

Status: Verified on a clean PostgreSQL database.

## Migration Scope

- `20260621_partner_attribution_hardening` adds
  `partner_attribution_sessions.capture_idempotency_key_hash`,
  `partner_attribution_sessions.consumed_transfer_token_hash`, and uniqueness
  guardrails for nullable session hashes, attribution touchpoint idempotency,
  source-event keys, and active commercial-binding owner uniqueness.
- `20260621_partner_code_links` adds durable partner code links used for public
  link and QR attribution surfaces.
- `20260621_partner_comm_contracts` adds immutable partner commission contract
  persistence used for payment-to-earning calculations.
- `20260621_partner_slug_required` requires partner code public slugs after the
  link backfill.
- `20260622_partner_owner_ranges` enforces active commercial-owner effective
  range constraints.

## PostgreSQL Preflight Checks

The migrations fail closed when duplicate active commercial-binding owners,
duplicate touchpoint idempotency/source-event keys, or overlapping active owner
ranges would violate the new PostgreSQL indexes/constraints. Conflicting data
must be cleaned before upgrade instead of silently choosing a winner.

## Verification Executed

| Check | Result |
| --- | --- |
| Clean upgrade | `alembic upgrade head` on a new PostgreSQL database reached `20260622_partner_owner_ranges (head)` |
| Downgrade | `alembic downgrade -1` moved the clean database back to `20260621_partner_slug_required` |
| Re-upgrade | `alembic upgrade head` returned the database to `20260622_partner_owner_ranges (head)` |
| PostgreSQL attribution constraints and concurrency | `test_partner_attribution_claim_postgres.py` passed on a clean migrated PostgreSQL database |
| PostgreSQL commission contract migration behavior | `test_partner_commission_contracts_migration_postgres.py` passed on a clean migrated PostgreSQL database |
| Full backend regression | `pytest tests -v --tb=short` passed with 2230 passed and 79 skipped |

## Rollback Notes

- Downgrading `20260622_partner_owner_ranges` removes the active owner range
  enforcement and returns to `20260621_partner_slug_required`.
- Earlier replay-state downgrade drops the added indexes and columns. It does
  not reconstruct active transfer-token hashes from consumed hashes, so
  replay-state history would be removed on downgrade.
- Rollback must be paired with an operational check for duplicate active owner
  ranges before any later re-upgrade.
