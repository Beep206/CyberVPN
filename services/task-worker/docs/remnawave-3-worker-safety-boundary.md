# Remnawave 3 worker safety boundary

The Remnawave 3.4.3 cutover makes numeric identity canonical and treats the
legacy UUID as an exact rollback binding. Scheduled code must not enumerate a
provider page and then mutate or notify from provider-owned Telegram metadata.

## Active safe workflow

`auto_renew_subscriptions` performs a bounded, cycle-detecting
`/api/users/stream` read. It submits only numeric identity and observed expiry
to the backend. The backend then:

1. resolves one active `MobileUser` with an exact mapped numeric and legacy
   identity pair;
2. verifies the authoritative upstream response against both identifiers and
   a two-hour past/future eligibility window;
3. creates or reuses the invoice under the expiry idempotency key; and
4. atomically queues one Telegram delivery using the backend-owned recipient.

The worker receives only `payment_id`, replay state, and a notification receipt.
It never receives the payment URL or Telegram recipient.

## Redis Stream privacy and authority boundary

The Remnawave export Valkey is an at-least-once transport, not an independent
source of truth. CyberVPN's committed database projection is authoritative;
epoch/range loss and trimmed pending entries use the bounded Remnawave REST
reconciliation workflow. The deployment contract permits exactly one consumer
group, `cybervpn-remnawave-v1`, for `subscription_requests`. Do not add a
second group unless a durable privacy-preserving fan-out replaces source-entry
sharing.

`subscription_requests` carries raw `requestIp` and User-Agent. Its terminal
ordering is therefore fixed:

1. a new or reclaimed entry remains in the PEL and source stream while it is
   parsed and projected;
2. after the idempotent backend projection commits, one Redis transaction
   performs `XACK` and `XDEL` for the source ID;
3. for a permanent contract failure, the backend first commits a redacted DLQ
   receipt, then one Redis transaction performs redacted `XADD`, `XACK`, and
   `XDEL`; and
4. any parse-to-DLQ persistence failure or event persistence failure leaves the
   entry pending and undeleted for bounded reclaim/retry.

The DLQ stores only stream/message identity, safe schema/error taxonomy,
delivery count, timestamp, and a domain-separated HMAC payload fingerprint.
It never stores raw IP, User-Agent, or source fields. `user_usage` and
`node_connections` retain their existing `XACK`-only behavior; their source
lifecycle remains controlled by the upstream bounded stream policy.

## Temporarily safety-disabled workflows

The registered tasks below return `safety_disabled=true`, a stable `reason`,
and zero processed/mutated/notified counts. They intentionally perform no
database, Remnawave, CryptoBot, Redis, SSE, or Telegram I/O:

- `check_expiring_subscriptions`;
- `disable_expired_users`;
- `process_payment_completion`;
- `verify_pending_payments`;
- `retry_failed_webhooks`;
- `bulk_disable_users`;
- `bulk_enable_users`.

This is an interim release blocker, not successful adoption of those
capabilities. Alert on any `*_safety_disabled` log event.

`reset_monthly_traffic` is separately closed as `not_applicable`. Every
authoritative paid, trial, manual and gift provisioning contract uses
`trafficLimitStrategy=NO_RESET`, so the legacy task name is retained only for
queued/manual compatibility and is deliberately absent from the cron schedule.
It returns zero work with
`reason=backend_subscription_traffic_policy_is_no_reset` and performs no I/O.

## Required replacement contracts

Do not re-enable these tasks until the backend owns and tests the corresponding
durable workflow:

- `RemnawaveScheduledCustomerOperationSaga`: bounded selection from local
  subjects, exact numeric+legacy ledger resolution, local eligibility policy,
  one mutation receipt per subject/operation/period, ambiguous-response
  reconciliation by exact GET, and canonical notification outbox delivery.
- `PaymentCompletionSaga`: durable per-payment states for provider verification,
  exact identity resolution, subscription extension, enablement, payment
  completion, canonical notification outbox, and event publication. Every step
  must be resumable and idempotent; a payment must not become `completed` until
  required VPN effects are authoritatively confirmed or explicitly held in a
  reconciliation state.
- `BulkUserOperationSaga`: one backend-authorized opaque job, immutable bounded
  subjects, per-service-identity generation/lease/receipt state, serialization
  with provisioning and opposite bulk transitions, exact GET reconciliation,
  and atomic local transition, audit and notification/event outbox persistence.

Required tests include foreign/unmapped/service identities, split numeric/UUID
bindings, empty/202 and transport-ambiguous provider responses, concurrent and
replayed scheduler deliveries, canonical-recipient reassignment, pagination
cursor cycles, partial provider success, crash/restart between every durable
step, and zero notification before the owning transaction commits.

## Audited blocker for the remaining subscription scheduler pair

The reminder and expiry-disable jobs cannot be restored by translating the legacy UUID
calls to numeric routes. The current persistence does not contain a durable
scheduled-operation receipt, and the local access-expiry authority is not one
column:

- canonical paid access is represented by one or more realm-scoped
  `entitlement_grants` and subscription-scoped `service_identities`;
- legacy paid access is derived from `payments.created_at + subscription_days`;
- trial access uses `mobile_users.trial_expires_at`;
- the provider exposes its own `expireAt`, `status`, and
  `lastTrafficResetAt` observations.

`Stage1ExpiryGraceWorker` is a policy evaluator plus an injected mutation
gateway. It deliberately has no bounded local selector, durable claim/lease,
operation receipt, notification outbox transaction, or scheduler route. It is
therefore not a runnable replacement for `disable_expired_users`. In
particular, merely invoking it from task-worker would still permit a renewal to
race an expiry disable between the eligibility read and the provider PATCH.

The existing notification queue also cannot be used as the operation ledger:
it has no subject/period idempotency constraint, and canonical-recipient
revalidation is currently defined only for subject-bound auto-renew rows.
Restoring these jobs consequently requires both an expand migration and the
following product decisions. Until they are made and migrated, keeping all
remaining lifecycle tasks observably safety-disabled is the fail-closed behavior.

1. Define the precedence/migration rule between canonical entitlement grants,
   legacy payment-derived expiry, trial expiry, and provider expiry.
2. Define which realm/subscription service identity owns a customer mutation
   when more than one identity or grant exists.
3. Confirm reminder brackets, localization, delivery channels, and paid/trial
   grace semantics from backend-owned policy rather than provider metadata.
4. Make renewal/provisioning and expiry mutation paths share the same
   per-service-identity serialization boundary so a concurrent extension
   cannot be disabled by a stale scheduler observation.

## Minimal replacement design

Add a backend-owned `remnawave_scheduled_customer_operations` ledger with a
unique operation key over `(operation, service_identity_id, policy_period)`, an
immutable exact numeric/legacy identity snapshot, expected local/provider
postconditions, state, bounded attempt count, claim lease, redacted terminal
reason, notification queue reference, and timestamps. No raw provider payload,
subscription URL, Telegram recipient, or secret belongs in this ledger.

The backend scheduler endpoint must then perform a bounded cursor-based local
selection and, for every subject:

1. resolve exactly one local entitlement and mapped subscription identity;
2. atomically create or claim the period receipt with `SKIP LOCKED` semantics;
3. perform an exact numeric provider GET and reject split identity or stale
   expiry observations;
4. mutate only a claimed receipt, never by replaying an ambiguous request;
5. reconcile disable via exact status after any ambiguous provider outcome;
6. commit the terminal receipt, local entitlement transition, canonical
   subject-bound notification row, and audit/outbox state together; and
7. expose only bounded counts and replay/reconciliation status to task-worker.

The TaskIQ jobs then become thin authenticated calls to that backend endpoint.
They must never scan provider users, choose recipients, access the worker
database, call Remnawave mutations, or send Telegram directly. Transient
backend failures retain normal TaskIQ retry semantics; a committed replay or
terminal reconciliation result is acknowledged without repeating a provider
mutation.
