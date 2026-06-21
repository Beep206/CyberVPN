---
name: cybervpn-migration-safety
description: Design and verify safe CyberVPN SQLAlchemy/Alembic schema migrations, data backfills, indexes, constraints, and rollback behavior.
---

# Migration Safety

1. Inspect current models, repository queries, existing migrations and production-size implications.
2. Define invariants, compatibility window, lock risk, backfill strategy and rollback behavior.
3. Prefer database-enforced constraints for uniqueness/idempotency and concurrency safety.
4. Avoid importing current ORM models into migrations; define migration-time schema explicitly.
5. Make existing-row backfills deterministic and restart-safe. Bound batches for potentially large tables.
6. Test on PostgreSQL:
   - clean upgrade to head;
   - upgrade from previous head with representative existing data;
   - invariant and index/constraint behavior;
   - downgrade;
   - re-upgrade.
7. Add concurrent tests for unique active bindings, claims, payments, settlements or other race-prone state.
8. Inspect generated SQL/locks when the operation may block production traffic.
9. Document truly irreversible behavior and require an approved ADR; do not fake downgrade support.
10. Record exact database commands and evidence in the task contract.
