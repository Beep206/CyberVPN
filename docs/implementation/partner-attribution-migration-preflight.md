# Partner Attribution Migration Preflight

Task: `PARTNER-ATTRIBUTION-HARDENING`

Migration: `backend/alembic/versions/20260621_partner_attribution_hardening.py`

Status: Partial verification only.

## Migration Scope

- Adds `partner_attribution_sessions.capture_idempotency_key_hash`.
- Adds `partner_attribution_sessions.consumed_transfer_token_hash`.
- Adds unique indexes for the new nullable session hashes.
- Adds PostgreSQL partial unique indexes for attribution touchpoint idempotency and source-event keys.
- Adds PostgreSQL partial unique indexes for active commercial-binding owner uniqueness at global and storefront scopes.

## PostgreSQL Preflight Checks

The migration checks for duplicate active commercial-binding owners and duplicate touchpoint idempotency/source-event keys before creating PostgreSQL partial unique indexes. If conflicting data exists, upgrade raises a clear migration error rather than silently picking a winner.

## Verification Executed

- `cd backend && alembic heads` reported `20260621_partner_attr_hardening (head)`.
- `cd backend && python -m py_compile alembic/versions/20260621_partner_attribution_hardening.py` exited successfully.
- Touched-file Ruff check and format check passed for the migration.

## Verification Not Yet Executed

- Clean PostgreSQL upgrade to the new head.
- Schema inspection after upgrade.
- Preflight duplicate-data failure rehearsal.
- Downgrade and rollback schema inspection.
- Re-upgrade after downgrade.
- Concurrent uniqueness tests against PostgreSQL.

## Rollback Notes

The downgrade drops the added indexes and columns. It does not reconstruct active transfer-token hashes from consumed hashes, so replay-state history would be removed on downgrade.
