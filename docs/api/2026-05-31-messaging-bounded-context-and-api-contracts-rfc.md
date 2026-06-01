# CYBA-247.1 RFC: messaging bounded context and API contracts

**Date:** 2026-05-31
**Issue:** `CYBA-248` / `CYBA-247.1`
**Status:** contract-first RFC for implementation tasks
**Approved plan revision:** `5d474011-187b-424b-bb9e-fe21ce58d549`
**Owner:** Orion CTO

This RFC freezes the first implementation contract for CyberVPN private admin-to-customer messaging and unified site notifications. It is intentionally contract-first: no production code, production secrets, production deploy, or customer data is required to accept this document.

## 1. Executive Summary

CyberVPN should add a separate `messaging` bounded context for private admin-initiated conversations, customer replies, read state, unified in-site notifications, and broadcast foundations.

`support_tickets` remains a separate support/helpdesk domain. It already allows customer-created tickets and SLA/queue workflows, which conflicts with the private messaging invariant that a customer cannot start a private dialog. The two domains may link by identifier, but one must not be implemented by silently extending the other.

The source of truth is PostgreSQL. `outbox_events` and `outbox_publications` remain the durable publication boundary. NATS JetStream, WebSocket/SSE, Redis/Valkey, and Task Worker are delivery/projection mechanisms only; they must not store authoritative message history.

## 2. Decisions

Accepted by this RFC:

- Create a new `messaging` bounded context instead of converting `support_tickets` into private messaging.
- Use REST for commands and history sync; use WebSocket/SSE only for downstream event delivery.
- Persist conversations, messages, read states, site notifications, and broadcast materialization in PostgreSQL.
- Reuse existing `outbox_events` / `outbox_publications` for business-critical propagation.
- Require explicit admin RBAC/scopes for conversation read/create/write/assign/close, internal notes, and broadcast operations.
- Keep internal notes out of customer REST responses, customer realtime payloads, notification text, and broad event payloads.

Explicit non-goals for v1:

- User-to-user chat.
- Customer-created private conversations.
- Attachments, voice/video, E2E encryption, or rich HTML rendering.
- Production Telegram/email/mobile push enablement.
- Migrating historical `support_tickets` into `messaging`.

## 3. Bounded Context Boundary

### 3.1 Owns

`messaging` owns:

- admin-created private conversations with customers;
- participant membership and assignment;
- public messages visible to conversation participants;
- admin-only internal notes inside private conversations;
- per-participant read state and unread counters;
- in-site notifications derived from messages and domain events;
- broadcast campaign materialization for site notifications;
- outbox event creation for messaging and notification facts;
- REST sync cursors for missed events after reconnect.

### 3.2 Does Not Own

`messaging` does not own:

- customer-created support intake, SLA queues, legal/refund/abuse workflow, or public support references;
- payment, auth, VPN provisioning, Remnawave, subscription, or admin user lifecycle;
- external push providers such as Telegram, email, FCM/APNs;
- durable event transport infrastructure itself;
- general operational WebSocket monitoring topics.

### 3.3 Relationship To `support_tickets`

Current `support_tickets` tables and APIs remain authoritative for helpdesk/support:

- `support_tickets`
- `support_ticket_messages`
- `support_ticket_events`

Allowed integration:

- `messaging_conversations.related_support_ticket_id` may link a private conversation to a support ticket.
- A support workflow may ask an admin/system actor to open a private messaging conversation.
- An admin can reference a support ticket from a private message or internal note.

Forbidden integration:

- Do not expose `support_ticket_messages.visibility = internal` through customer messaging APIs.
- Do not let `POST /api/v1/support/tickets` create `messaging_conversations`.
- Do not make customer-created support tickets appear as private dialogs.
- Do not use `support_tickets.status` as the lifecycle state for private conversations.

## 4. Existing Repository Anchors

Implementation tasks should integrate with these existing patterns:

| Area | Existing anchor | RFC use |
|---|---|---|
| Support/helpdesk | `backend/alembic/versions/20260529_support_ticket_platform.py` | Keep separate; optional `related_support_ticket_id` link only |
| Support routes | `backend/src/presentation/api/v1/support_tickets/routes.py` | Pattern reference for ownership filters, not a shared implementation |
| Transactional outbox | `backend/src/infrastructure/database/models/outbox_event_model.py` | Reuse for messaging/notification events |
| Outbox contract | `docs/api/platform-foundation-outbox-contract.md` | Business facts must be written with the DB transaction |
| Event taxonomy | `docs/api/platform-foundation-event-taxonomy.md` | Envelope and subject rules apply; RFC extends domains for `messaging`, `notification`, `broadcast` |
| Realtime delivery | `docs/api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md` | Browser delivery is downstream of durable projection |
| Legacy notification queue | `backend/alembic/versions/20260422_notification_queue.py` | Existing Telegram/worker queue remains a delivery adapter, not the site notification source of truth |
| Admin permissions | `backend/src/application/use_cases/auth/permissions.py` | Add explicit messaging/notification permissions; do not rely on broad `USER_UPDATE` |
| WebSocket authz | `backend/src/application/services/ws_topic_authorization.py` | Add per-recipient/private channels with deny-by-default behavior |

## 5. Data Model Contract

All table names below are frozen for v1 implementation unless SecurityEngineer review finds a concrete issue.

### 5.1 `messaging_conversations`

Authoritative conversation row.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Internal stable identifier |
| `public_id` | `varchar(40)` unique | Customer/admin safe reference |
| `customer_account_id` | `uuid` FK `mobile_users.id` | Required; the only customer participant in v1 |
| `status` | enum string | `open`, `closed`, `archived`, `locked` |
| `response_state` | enum string | `none`, `waiting_customer`, `waiting_admin` |
| `category` | enum string | `support`, `billing`, `subscription`, `security`, `system`, `other` |
| `priority` | enum string | `low`, `normal`, `high`, `urgent` |
| `subject` | `varchar(160)` | Plain text, no HTML |
| `created_by_admin_id` | `uuid` FK `admin_users.id` | Required for admin-created conversation; nullable only for approved system-created rows |
| `assigned_admin_id` | `uuid` FK `admin_users.id`, nullable | Current owner |
| `related_support_ticket_id` | `uuid` FK `support_tickets.id`, nullable | Link only; no shared lifecycle |
| `last_message_id` | `uuid`, nullable | FK to `messaging_messages.id` after both tables exist |
| `last_message_at` | `timestamptz`, nullable | Updated on public message/internal note according to visibility policy |
| `closed_at` | `timestamptz`, nullable | Set when status becomes `closed` |
| `metadata` | `jsonb` | Redacted operational metadata only |
| `created_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |

Minimum indexes/constraints:

- `unique(public_id)`
- `index(customer_account_id, status, updated_at)`
- `index(assigned_admin_id, status, updated_at)`
- `index(status, priority, category, updated_at)`
- `check(customer_account_id is not null)`
- `check(status in (...))`

### 5.2 `messaging_conversation_participants`

Membership and admin/team watchers.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable row identifier |
| `conversation_id` | `uuid` FK | Cascade delete in non-prod only; production deletion policy must be privacy-reviewed |
| `participant_type` | enum string | `customer`, `admin`, `team`, `system` |
| `participant_id` | `uuid`, nullable | Required for `customer` and `admin`; nullable for `team`/`system` if named in metadata |
| `role` | enum string | `customer`, `creator`, `assignee`, `watcher`, `system` |
| `can_read` | `boolean` | Default `true`; inactive participants cannot read new messages |
| `can_write` | `boolean` | Customer true only while conversation is open and participant owns it |
| `joined_at` | `timestamptz` | Server time |
| `left_at` | `timestamptz`, nullable | Soft leave |
| `metadata` | `jsonb` | No secrets |

Minimum indexes/constraints:

- `unique(conversation_id, participant_type, participant_id, role)` for active participants where `left_at is null`
- `index(participant_type, participant_id, can_read)`
- exactly one active `customer` participant per v1 conversation

### 5.3 `messaging_messages`

Message and internal-note rows.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable identifier |
| `public_id` | `varchar(40)` unique | Safe external reference |
| `conversation_id` | `uuid` FK | Required |
| `sender_type` | enum string | `customer`, `admin`, `system` |
| `sender_id` | `uuid`, nullable | Required for customer/admin |
| `visibility` | enum string | `public`, `internal` |
| `body` | `text` | Plain text; escaped by clients; max length set by implementation |
| `body_format` | enum string | v1 only `plain_text` |
| `client_message_id` | `varchar(80)`, nullable | Required for customer/admin writes where client can generate it |
| `idempotency_key` | `varchar(160)` | Derived from actor + conversation + client id or `Idempotency-Key` |
| `reply_to_message_id` | `uuid`, nullable | Must be same conversation |
| `redacted_at` | `timestamptz`, nullable | Privacy/manual redaction marker |
| `created_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |
| `metadata` | `jsonb` | No tokens, VPN configs, provider IDs, or raw secrets |

Minimum indexes/constraints:

- `unique(conversation_id, sender_type, sender_id, client_message_id)` where `client_message_id is not null`
- `unique(idempotency_key)`
- `index(conversation_id, created_at)`
- `index(sender_type, sender_id, created_at)`
- `check(visibility = 'internal' implies sender_type in ('admin', 'system'))`

Customer-visible APIs must filter `visibility = 'public'`.

### 5.4 `messaging_message_read_states`

Per participant high-water read state.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable identifier |
| `conversation_id` | `uuid` FK | Required |
| `participant_type` | enum string | `customer`, `admin`, `team` |
| `participant_id` | `uuid` | Required for customer/admin |
| `last_read_message_id` | `uuid` FK, nullable | Must belong to same conversation and be readable by participant |
| `last_read_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |

Minimum indexes/constraints:

- `unique(conversation_id, participant_type, participant_id)`
- `index(participant_type, participant_id, updated_at)`

### 5.5 `site_notifications`

Canonical in-site notification fact.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable identifier |
| `notification_type` | enum string | `message`, `system`, `billing`, `subscription`, `security`, `broadcast` |
| `severity` | enum string | `info`, `success`, `warning`, `critical` |
| `title` | `varchar(160)` | Safe display text or template-rendered text |
| `body` | `text`, nullable | Safe display text; no secrets or VPN configs |
| `action_url` | `varchar(500)`, nullable | Relative application URL only unless approved |
| `aggregate_type` | `varchar(80)`, nullable | Example: `messaging_conversation`, `support_ticket`, `payment_attempt` |
| `aggregate_id` | `varchar(160)`, nullable | Redacted stable id/reference |
| `conversation_id` | `uuid`, nullable | FK if message-derived |
| `message_id` | `uuid`, nullable | FK if message-derived |
| `broadcast_campaign_id` | `uuid`, nullable | FK if broadcast-derived |
| `created_by_actor_type` | enum string | `admin`, `system`, `worker` |
| `created_by_actor_id` | `uuid`, nullable | No customer-created notifications in v1 except via system facts |
| `payload` | `jsonb` | Minimal display metadata; no raw provider/customer secrets |
| `expires_at` | `timestamptz`, nullable | Required for ephemeral announcements when applicable |
| `created_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |

### 5.6 `site_notification_deliveries`

Per-recipient in-site notification state and future delivery adapter state.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable identifier |
| `notification_id` | `uuid` FK | Required |
| `recipient_type` | enum string | `customer`, `admin`, `team` |
| `recipient_id` | `uuid`, nullable | Required for customer/admin |
| `delivery_channel` | enum string | v1 `site`; future `telegram`, `email`, `push` |
| `status` | enum string | `pending`, `delivered`, `read`, `dismissed`, `failed`, `expired` |
| `delivered_at` | `timestamptz`, nullable | Realtime/browser delivery evidence, not source of truth |
| `read_at` | `timestamptz`, nullable | User read marker |
| `dismissed_at` | `timestamptz`, nullable | User dismissal marker |
| `attempts` | `integer` | Delivery attempts for worker adapters |
| `last_error` | `text`, nullable | Sanitized |
| `created_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |

Minimum indexes/constraints:

- `unique(notification_id, recipient_type, recipient_id, delivery_channel)`
- `index(recipient_type, recipient_id, status, created_at)`
- `index(status, created_at)` for worker scans

### 5.7 `broadcast_campaigns`

Admin/system campaign definition.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable identifier |
| `public_id` | `varchar(40)` unique | Safe admin reference |
| `name` | `varchar(160)` | Admin label |
| `status` | enum string | `draft`, `scheduled`, `sending`, `sent`, `cancelled`, `failed` |
| `audience_type` | enum string | `all_customers`, `customer_segment`, `explicit_customers`, `admins` |
| `audience_filter` | `jsonb` | Only approved structured filters; no raw SQL |
| `template_key` | `varchar(120)`, nullable | Preferred over ad hoc text |
| `title` | `varchar(160)` | Safe text |
| `body` | `text` | Safe text |
| `action_url` | `varchar(500)`, nullable | Relative URL unless approved |
| `scheduled_at` | `timestamptz`, nullable | Required for scheduled campaigns |
| `created_by_admin_id` | `uuid` FK | Required for admin-created broadcasts |
| `approved_by_admin_id` | `uuid`, nullable | Required if Board/Security policy demands approval for broad sends |
| `cancelled_at` | `timestamptz`, nullable | Set on cancel |
| `created_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |
| `metadata` | `jsonb` | No secrets |

### 5.8 `broadcast_campaign_recipients`

Materialized campaign recipients.

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` PK | Stable identifier |
| `campaign_id` | `uuid` FK | Required |
| `recipient_type` | enum string | `customer`, `admin` |
| `recipient_id` | `uuid` | Required |
| `site_notification_id` | `uuid`, nullable | Set after notification creation |
| `status` | enum string | `pending`, `created`, `skipped`, `failed`, `cancelled` |
| `skip_reason` | `varchar(160)`, nullable | Sanitized |
| `failure_reason` | `text`, nullable | Sanitized |
| `materialized_at` | `timestamptz` | Server time |
| `created_at` | `timestamptz` | Server time |
| `updated_at` | `timestamptz` | Server time |

Minimum indexes/constraints:

- `unique(campaign_id, recipient_type, recipient_id)`
- `index(campaign_id, status)`
- `index(recipient_type, recipient_id, created_at)`

## 6. REST API Contracts

### 6.1 Common Conventions

- Base path: `/api/v1`.
- Request correlation: `X-Request-ID`.
- Idempotent writes: `Idempotency-Key` header plus body-level `client_message_id` where applicable.
- Error envelope should follow the canonical baseline:

```json
{
  "error": {
    "code": "messaging_conversation_not_found",
    "message": "Conversation not found"
  },
  "request_id": "req_123"
}
```

Recommended error codes:

| Code | HTTP | Use |
|---|---:|---|
| `messaging_conversation_not_found` | 404 | Absent or outside caller scope |
| `messaging_conversation_closed` | 409 | Write attempted against closed/locked conversation |
| `messaging_customer_cannot_start_conversation` | 403 | Any customer private-conversation creation attempt |
| `messaging_internal_note_forbidden` | 403 | Non-admin attempts internal note access/write |
| `messaging_duplicate_client_message` | 409 or 200 | Duplicate idempotent write, implementation must choose deterministic response |
| `notification_not_found` | 404 | Notification absent or outside recipient scope |
| `broadcast_forbidden` | 403 | Missing broadcast scope |
| `broadcast_invalid_audience` | 422 | Unsupported or unsafe audience filter |

### 6.2 Customer Endpoints

Customers can list/read their conversations, reply to open conversations they participate in, mark reads, and manage their site notifications. There is deliberately no `POST /api/v1/me/conversations`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/me/conversations` | List caller-owned private conversations |
| `GET` | `/api/v1/me/conversations/{conversation_id}` | Get one caller-owned conversation with public messages |
| `POST` | `/api/v1/me/conversations/{conversation_id}/messages` | Reply in caller-owned open conversation |
| `POST` | `/api/v1/me/conversations/{conversation_id}/read` | Mark public messages read up to a message |
| `GET` | `/api/v1/me/notifications` | List caller site notifications |
| `POST` | `/api/v1/me/notifications/read` | Mark notification deliveries read |
| `POST` | `/api/v1/me/notifications/dismiss` | Dismiss notification deliveries |
| `GET` | `/api/v1/me/realtime/sync` | REST recovery after reconnect using cursor |

Customer list query:

```text
GET /api/v1/me/conversations?status=open&cursor=...&limit=50
```

Customer message create request:

```json
{
  "client_message_id": "web_01J00000000000000000000001",
  "body": "I still cannot connect after renewal."
}
```

Customer message create response:

```json
{
  "message": {
    "id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a",
    "conversation_id": "0c724d64-6322-4607-8220-bf4e59ad1954",
    "sender_type": "customer",
    "visibility": "public",
    "body": "I still cannot connect after renewal.",
    "created_at": "2026-05-31T14:30:00Z"
  },
  "conversation": {
    "id": "0c724d64-6322-4607-8220-bf4e59ad1954",
    "status": "open",
    "response_state": "waiting_admin"
  }
}
```

Customer read request:

```json
{
  "last_read_message_id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a"
}
```

Notification read request:

```json
{
  "notification_ids": ["2f7c50cf-1ce4-4d4d-9c36-47c94f9d62d4"],
  "read_all_before": null
}
```

REST sync query:

```text
GET /api/v1/me/realtime/sync?cursor=msg:2026-05-31T14:30:00Z:0f6b5c8e
```

REST sync response:

```json
{
  "cursor": "msg:2026-05-31T14:32:10Z:8d1b",
  "conversations": [],
  "messages": [],
  "notifications": [],
  "unread_counts": {
    "conversations": 1,
    "notifications": 3
  }
}
```

### 6.3 Admin Endpoints

Admin endpoints require explicit messaging/notification permissions. Internal notes are admin-only.

| Method | Path | Purpose | Required scope |
|---|---|---|---|
| `GET` | `/api/v1/admin/messaging/conversations` | Search/filter conversations | `messaging:conversation:read` |
| `POST` | `/api/v1/admin/messaging/conversations` | Create admin-initiated conversation | `messaging:conversation:create` |
| `GET` | `/api/v1/admin/messaging/conversations/{conversation_id}` | Get full admin conversation view | `messaging:conversation:read` |
| `POST` | `/api/v1/admin/messaging/conversations/{conversation_id}/messages` | Send public admin message | `messaging:message:write` |
| `POST` | `/api/v1/admin/messaging/conversations/{conversation_id}/internal-notes` | Add admin-only note | `messaging:internal_note:write` |
| `POST` | `/api/v1/admin/messaging/conversations/{conversation_id}/read` | Mark admin read state | `messaging:conversation:read` |
| `PATCH` | `/api/v1/admin/messaging/conversations/{conversation_id}` | Assign, recategorize, reprioritize | `messaging:conversation:assign` or `messaging:conversation:manage` |
| `POST` | `/api/v1/admin/messaging/conversations/{conversation_id}/close` | Close conversation | `messaging:conversation:close` |
| `POST` | `/api/v1/admin/messaging/conversations/{conversation_id}/reopen` | Reopen conversation | `messaging:conversation:close` |
| `GET` | `/api/v1/admin/notifications` | List admin notifications | `notification:site:read` |
| `POST` | `/api/v1/admin/notifications/read` | Mark admin notifications read | `notification:site:read` |
| `POST` | `/api/v1/admin/notifications/broadcasts` | Create/schedule broadcast | `notification:broadcast:create` |
| `GET` | `/api/v1/admin/notifications/broadcasts/{campaign_id}` | Inspect campaign | `notification:broadcast:read` |
| `POST` | `/api/v1/admin/notifications/broadcasts/{campaign_id}/cancel` | Cancel campaign | `notification:broadcast:cancel` |

Admin create conversation request:

```json
{
  "customer_account_id": "33333333-3333-4333-8333-333333333333",
  "subject": "VPN access after renewal",
  "category": "subscription",
  "priority": "normal",
  "assigned_admin_id": "44444444-4444-4444-8444-444444444444",
  "related_support_ticket_id": null,
  "initial_message": {
    "client_message_id": "admin_01J00000000000000000000001",
    "body": "Your renewal is complete. Please reopen the app and try again."
  }
}
```

Admin internal note request:

```json
{
  "client_message_id": "admin_note_01J00000000000000000000002",
  "body": "Do not send config URLs in chat. Ask customer to open the secure devices page."
}
```

Admin update request:

```json
{
  "assigned_admin_id": "44444444-4444-4444-8444-444444444444",
  "priority": "high",
  "category": "billing"
}
```

Broadcast create request:

```json
{
  "name": "Maintenance notice EU region",
  "audience_type": "customer_segment",
  "audience_filter": {
    "region": "eu",
    "has_active_subscription": true
  },
  "title": "Maintenance window",
  "body": "EU routes may reconnect once during the maintenance window.",
  "action_url": "/status",
  "scheduled_at": "2026-06-02T01:00:00Z"
}
```

## 7. Event Taxonomy And Outbox Contract

Messaging events are business facts and must be appended to `outbox_events` in the same transaction as the state change.

Canonical envelope follows `docs/api/platform-foundation-event-taxonomy.md`:

```json
{
  "event_id": "01J00000000000000000000001",
  "event_type": "messaging.message.created",
  "event_version": 1,
  "subject": "messaging.message.created.v1",
  "source": "backend-api",
  "occurred_at": "2026-05-31T14:30:00Z",
  "environment": "staging",
  "aggregate_type": "messaging_message",
  "aggregate_id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a",
  "correlation_id": "req_123",
  "idempotency_key": "messaging_message:0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a",
  "pii_classification": "restricted",
  "schema_ref": "docs/api/2026-05-31-messaging-bounded-context-and-api-contracts-rfc.md#messagingmessagecreatedv1",
  "payload": {}
}
```

Important naming note: this RFC uses the task notation `messaging.message.created.v1` for the logical event subject. In the canonical envelope, `event_type` is `messaging.message.created`.

CYBA-276 implementation exception: the current backend JetStream publication subject is consumer-scoped as `messaging.{consumer_key}.{event_type}.v{schema_version}`, for example `messaging.messaging_realtime_projection.messaging.message.created.v1`. This keeps the existing outbox-publication model one durable publication per consumer and lets each durable consumer filter its own subject branch. The logical event contract remains `event_type=messaging.message.created` with schema version `1`; browser and REST clients must not depend on the JetStream consumer segment.

### 7.1 Subjects

| Subject | Required | Aggregate | Payload rule | Initial consumers |
|---|---|---|---|---|
| `messaging.conversation.created.v1` | yes | `messaging_conversation` | IDs/status/category only | realtime projection, notification fanout, audit projection |
| `messaging.message.created.v1` | yes | `messaging_message` | No raw body for broad transport; authorized realtime projection fetches body by id | realtime projection, notification fanout, audit projection |
| `messaging.message.read.v1` | yes | `messaging_read_state` | Reader and high-water id only | realtime projection, unread counter projection |
| `messaging.conversation.assigned.v1` | related | `messaging_conversation` | Admin ids and assignment state | admin realtime projection, audit projection |
| `messaging.conversation.closed.v1` | related | `messaging_conversation` | Status transition only | realtime projection, audit projection |
| `messaging.conversation.reopened.v1` | related | `messaging_conversation` | Status transition only | realtime projection, audit projection |
| `notification.created.v1` | yes | `site_notification` | Safe display fields and recipient refs only | realtime projection, delivery worker |
| `notification.read.v1` | related | `site_notification_delivery` | Recipient and read marker only | realtime projection, analytics projection |
| `notification.dismissed.v1` | related | `site_notification_delivery` | Recipient and dismissal marker only | realtime projection |
| `broadcast.created.v1` | yes | `broadcast_campaign` | Campaign metadata, no materialized recipient list | broadcast fanout worker, audit projection |
| `broadcast.cancelled.v1` | related | `broadcast_campaign` | Campaign id and cancellation metadata | broadcast fanout worker, audit projection |
| `broadcast.recipient.created.v1` | related | `broadcast_campaign_recipient` | Recipient id/type and notification id | delivery worker, analytics projection |

### 7.2 Payload Shapes

#### `messaging.conversation.created.v1`

```json
{
  "conversation_id": "0c724d64-6322-4607-8220-bf4e59ad1954",
  "public_id": "msg_9K8H2Q",
  "customer_account_id": "33333333-3333-4333-8333-333333333333",
  "created_by_admin_id": "44444444-4444-4444-8444-444444444444",
  "assigned_admin_id": "44444444-4444-4444-8444-444444444444",
  "status": "open",
  "response_state": "waiting_customer",
  "category": "subscription",
  "priority": "normal",
  "related_support_ticket_id": null
}
```

#### `messaging.message.created.v1`

```json
{
  "conversation_id": "0c724d64-6322-4607-8220-bf4e59ad1954",
  "message_id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a",
  "sender_type": "admin",
  "sender_id": "44444444-4444-4444-8444-444444444444",
  "visibility": "public",
  "recipient_refs": [
    {
      "recipient_type": "customer",
      "recipient_id": "33333333-3333-4333-8333-333333333333"
    }
  ],
  "body_included": false
}
```

`body_included` must remain `false` for broad durable event transport unless SecurityEngineer approves a narrower encrypted/private stream. Authorized delivery adapters should fetch the message by id and apply recipient checks before rendering.

#### `messaging.message.read.v1`

```json
{
  "conversation_id": "0c724d64-6322-4607-8220-bf4e59ad1954",
  "participant_type": "customer",
  "participant_id": "33333333-3333-4333-8333-333333333333",
  "last_read_message_id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a",
  "last_read_at": "2026-05-31T14:31:00Z"
}
```

#### `notification.created.v1`

```json
{
  "notification_id": "2f7c50cf-1ce4-4d4d-9c36-47c94f9d62d4",
  "notification_type": "message",
  "severity": "info",
  "recipient_type": "customer",
  "recipient_id": "33333333-3333-4333-8333-333333333333",
  "aggregate_type": "messaging_message",
  "aggregate_id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a",
  "conversation_id": "0c724d64-6322-4607-8220-bf4e59ad1954",
  "delivery_id": "cb702c35-f26b-4bb5-b818-948b2a0c5c48"
}
```

#### `broadcast.created.v1`

```json
{
  "campaign_id": "d22d0b93-1782-487d-96c3-2e66be1b48aa",
  "public_id": "bcast_3W7X9Q",
  "status": "scheduled",
  "audience_type": "customer_segment",
  "scheduled_at": "2026-06-02T01:00:00Z",
  "created_by_admin_id": "44444444-4444-4444-8444-444444444444",
  "recipient_count_estimate": 1200
}
```

### 7.3 Consumer Keys

Initial `outbox_publications.consumer_key` values:

- `messaging_realtime_projection`
- `site_notification_fanout`
- `broadcast_fanout_worker`
- `messaging_audit_projection`

Every consumer must be idempotent. Duplicate event delivery must not create duplicate messages, notifications, read states, campaign recipients, or browser toasts.

## 8. Realtime And Sync

### 8.1 Canonical Flow

```text
REST command
  -> PostgreSQL transaction
      -> messaging/site notification state
      -> outbox_events + outbox_publications
  -> outbox dispatcher
  -> durable event transport/projection
  -> WebSocket/SSE delivery
  -> REST sync for missed state
```

Rules:

- REST is the write path.
- WebSocket/SSE never creates messages or read state directly.
- Browser delivery is not evidence of durable publication.
- `Last-Event-ID`/cursor sync is a delivery aid, not source of truth.
- Redis/Valkey may hold presence, connection registry, rate limits, and short-lived counters only.

### 8.2 Channels

Customer channels:

- `customer:{customer_account_id}:messaging`
- `customer:{customer_account_id}:notifications`

Admin channels:

- `admin:{admin_id}:messaging`
- `admin:{admin_id}:notifications`
- `admin:team:{team_id}:messaging` only after SecurityEngineer approves team membership checks

Forbidden:

- wildcard customer subscriptions;
- customer subscribing by arbitrary `customer_account_id`;
- exposing admin/team/internal channels to customer tokens;
- sending `visibility = internal` messages to customer channels.

### 8.3 Delivery Payload

Realtime payloads should be small and recipient-scoped:

```json
{
  "event_id": "01J00000000000000000000001",
  "channel": "customer:33333333-3333-4333-8333-333333333333:messaging",
  "event_type": "messaging.message.created",
  "cursor": "msg:2026-05-31T14:30:00Z:0f6b5c8e",
  "payload": {
    "conversation_id": "0c724d64-6322-4607-8220-bf4e59ad1954",
    "message_id": "0f6b5c8e-3b6e-4f13-a441-880e0e1d2f1a"
  }
}
```

The client should call REST detail/sync when the payload is insufficient or when it detects a cursor gap.

## 9. RBAC Matrix

### 9.1 Proposed Scopes

| Scope | Allows |
|---|---|
| `messaging:conversation:read` | Admin list/detail/search conversation access |
| `messaging:conversation:create` | Admin creates private conversation |
| `messaging:message:write` | Admin sends public message |
| `messaging:internal_note:write` | Admin writes internal-only note |
| `messaging:conversation:assign` | Admin assigns/reassigns owner |
| `messaging:conversation:close` | Admin closes/reopens |
| `messaging:conversation:manage` | Admin category/priority/status management |
| `notification:site:read` | Admin reads own/admin site notifications |
| `notification:broadcast:read` | Admin inspects campaigns |
| `notification:broadcast:create` | Admin creates/schedules campaigns |
| `notification:broadcast:cancel` | Admin cancels campaigns |
| `notification:analytics:read` | Admin reads messaging/notification analytics |

Recommended role mapping for implementation review:

| Role | Baseline scopes |
|---|---|
| `OWNER_SUPER_ADMIN` / `SUPER_ADMIN` | All scopes |
| `ADMIN` | All conversation scopes; broadcast create/cancel if Board approves |
| `SUPPORT` | Read/create/message/internal-note/assign/close for support-owned conversations; no broadcast |
| `OPERATOR` | Read/message for operational conversations only if assigned; no internal-note by default unless approved |
| `FINANCE` | Read/message for billing category conversations only if assigned; no broadcast |
| `VIEWER` | No private messaging by default; optional read-only admin notification scope |

Implementation must not map new write operations to broad `USER_UPDATE` without a documented temporary compatibility bridge and SecurityEngineer approval.

### 9.2 Mandatory Invariants

Customer invariants:

- Customer cannot create a private conversation.
- Customer can read only conversations where `customer_account_id = current_mobile_user_id`.
- Customer can reply only in their own conversation when `status = open`.
- Customer cannot reply to `closed`, `archived`, or `locked` conversations.
- Customer cannot choose an arbitrary admin recipient.
- Customer cannot see `visibility = internal` messages.
- Customer cannot subscribe to another customer, admin, team, or internal realtime channel.

Admin invariants:

- Admin endpoints require explicit scopes.
- Admin list/detail responses must be filtered by scope, assignment, category policy, or role policy.
- Internal notes require `messaging:internal_note:write`.
- Broadcast operations require explicit broadcast scopes and audit entries.
- Assignment/close/reopen/category/priority changes require audit entries.

System invariants:

- Message creation and outbox event creation are one transaction.
- Duplicate idempotency keys do not create duplicate rows.
- Notification delivery failure does not roll back committed messages.
- Realtime outage does not block REST history.
- NATS/worker outage leaves outbox backlog, not lost business events.
- Redis outage degrades presence/realtime only; persistence still works.

## 10. Threat Model

| Threat | Risk | Required mitigation |
|---|---|---|
| Cross-customer data leak | Customer reads another conversation | Query by authenticated owner; route tests for wrong-owner ids |
| Internal-note leak | Customer sees admin-only notes | `visibility` filter in repository/service; negative REST and realtime tests |
| Unauthorized realtime subscription | Token subscribes to private channel | Deny-by-default topic authorization; channel recipient must match token subject |
| Customer starts private dialog | Business invariant broken | No customer create route; service-level guard returns 403 if invoked |
| Message duplication | Retry creates duplicate messages | `client_message_id` and `idempotency_key` uniqueness |
| Event duplication | Consumer repeats side effects | Consumer receipts/idempotent upserts |
| XSS/message injection | Message body rendered as trusted HTML | Plain text v1; escape on clients; no Markdown/HTML until separately reviewed |
| PII/secrets in events/logs | Message body or VPN config enters outbox/logs | No raw message body in broad event payload; redaction in logs and metadata |
| Broadcast misfire | Wrong audience receives sensitive notice | Structured audience filters only, audit, optional approval for broad audience |
| Reconnect storm | Availability loss | Rate limits, backoff, cursor sync, load tests |
| Abuse/spam | Customer/admin floods messages/read/sync | Per actor/conversation rate limits |
| Retention/privacy conflict | Messages retained too long or deleted too early | Board-approved retention policy and privacy review before production |

## 11. Migration, Rollout, Rollback, Retention

### 11.1 Migration Boundaries

- Additive Alembic migrations only for v1.
- Do not drop or rewrite existing `support_tickets`, `notification_queue`, or outbox tables.
- Do not backfill support tickets into messaging without a separate Board-approved migration.
- Do not enable production data migration, production delivery channels, or production broadcast sends in these implementation tasks.
- All routes should be feature-flagged or config-gated for non-prod verification.

### 11.2 Rollout Sequence

1. Add tables and domain/service contracts behind disabled routes.
2. Add REST APIs with ownership/RBAC tests.
3. Add outbox events and consumers with local/non-prod dispatch tests.
4. Add realtime/SSE/WebSocket projection with per-recipient authorization tests.
5. Add frontend surfaces after API contracts are stable.
6. Run SecurityEngineer review before implementation MRs proceed to final acceptance.
7. Run QA browser/reconnect/offline validation.
8. Produce evidence/runbook before any release decision.

### 11.3 Rollback Assumptions

- If runtime rollout fails, disable routes/realtime consumers with feature flags and leave persisted rows intact.
- Outbox backlog can remain pending while disabled; workers must not delete pending events.
- Additive schema rollback is allowed only in non-prod after data export is deemed unnecessary.
- Production rollback must not drop communication history without owner/privacy approval.

### 11.4 Data Retention Assumptions

These are proposed defaults and require Board/privacy confirmation before production:

- `messaging_messages.body`: retain for 24 months after conversation closure, then redact body while keeping metadata unless legal/security hold applies.
- `messaging_messages.visibility = internal`: same retention as public messages unless SecurityEngineer/legal requires longer audit retention.
- `messaging_conversations`: retain metadata for 24 months after closure, then anonymize customer/admin ids where legally allowed.
- `site_notification_deliveries`: retain read/dismissed delivery rows for 180 days; retain unread active rows until `expires_at` or 365 days, whichever comes first.
- `broadcast_campaigns`: retain campaign metadata and template content for 24 months; recipient materialization rows for 180 days after completion.
- Account deletion/export workflows must be reviewed before production to decide whether messages are deleted, redacted, or retained under legal/security basis.

## 12. Implementation Blockers And Missing Inputs

Blockers before implementation MRs can be accepted:

- SecurityEngineer review for admin RBAC, ownership checks, WebSocket/SSE auth, internal-note leakage, broadcast privacy, rate limits, and retention.
- Event taxonomy update or explicit exception: current platform taxonomy freezes top-level domains without `messaging`, `notification`, or `broadcast`; this RFC proposes adding them for CYBA-247.
- Board/privacy confirmation of retention windows and account deletion/export behavior.
- Decision on whether broad broadcasts require two-person approval for `all_customers` and large `customer_segment` audiences.
- Final mapping from proposed scopes to `AdminRole` values and `Permission` enum names.

Non-blocking implementation notes:

- Backend should reuse `outbox_events` and `outbox_publications`; adding a new outbox table is not justified for v1.
- `notification_queue` may remain the worker adapter for Telegram-style delivery, but `site_notifications` / `site_notification_deliveries` should be the canonical in-app notification center.
- Message body should not be copied into broad outbox/NATS payloads unless a later security design narrows and protects the stream.

## 13. Verification Plan

Repo inspection completed for this RFC:

- Existing support ticket migration/routes/domain were inspected to keep support separate.
- Existing outbox model and outbox contract were inspected to reuse the durable publication boundary.
- Existing platform event taxonomy and realtime gateway spec were inspected to align envelope/realtime rules.
- Existing notification queue and admin permission/WebSocket authorization patterns were inspected for integration points.

Required verification for implementation tasks:

- Migration tests prove all eight new table groups are created with indexes/constraints.
- Service tests prove customer cannot create private conversation, cannot read another customer's conversation, and cannot post to closed conversation.
- Admin RBAC tests prove missing scopes cannot read/write/assign/close/broadcast.
- Internal-note negative tests prove customer REST and customer realtime never include internal notes.
- Idempotency tests prove duplicate `client_message_id` and duplicate outbox events do not duplicate writes.
- Outbox tests prove message/notification state and outbox rows commit atomically.
- Realtime tests prove unauthorized channel subscription is denied and REST sync recovers missed events.
- Broadcast tests prove audience filters are structured, audited, cancellable, and idempotent.
- Frontend/browser QA proves admin creates conversation, customer receives and replies, admin sees reply, internal note remains admin-only, closed conversation is read-only, and reconnect sync works.

Context7 docs checked: N/A - RFC/documentation-only task; no code, framework API, library API, package manager behavior, or runtime configuration was changed. Implementation tasks must query current Context7 docs before touching FastAPI, SQLAlchemy/Alembic, Pydantic, NATS, Redis, TaskIQ, Next.js, React, next-intl, TanStack Query, Vitest, or Playwright code.

## 14. Board Decisions Needed

1. Approve this RFC as the contract baseline for `CYBA-249`, `CYBA-256`, and downstream implementation tasks.
2. Confirm that `messaging`, `notification`, and `broadcast` are allowed event domains for CYBA-247, or instruct implementation to place transport subjects under a different existing platform domain.
3. Confirm retention assumptions in section 11.4 or provide alternate windows.
4. Decide whether broad broadcasts need two-person approval before send.
5. Confirm initial role-to-scope mapping, especially `SUPPORT`, `OPERATOR`, `FINANCE`, and `VIEWER`.

## 15. Acceptance Criteria Mapping

| Acceptance criterion | RFC coverage |
|---|---|
| Messaging bounded context boundaries | Sections 1-4 |
| Keep `support_tickets` separate | Sections 3.2-3.3 |
| Table names | Section 5 |
| Endpoint contracts | Section 6 |
| Event taxonomy | Section 7 |
| RBAC matrix | Section 9 |
| Mandatory invariants | Section 9.2 |
| Threat model | Section 10 |
| Migration boundaries | Section 11.1 |
| Rollback and data retention assumptions | Sections 11.3-11.4 |
| Security-sensitive surfaces identified | Sections 10 and 12 |
| Verification plan and Context7 evidence | Section 13 |
