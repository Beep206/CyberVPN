# Messaging Realtime Gateway

CYBA-253 adds authenticated per-recipient realtime transports for messaging events.

## Endpoints

- `POST /api/v1/me/realtime/ticket` creates a short-lived customer WebSocket ticket.
- `GET /api/v1/me/realtime/sse` opens the customer SSE fallback stream.
- `GET /api/v1/me/realtime/sync` remains the customer REST recovery endpoint.
- `POST /api/v1/admin/messaging/realtime/ticket` creates a short-lived admin WebSocket ticket.
- `GET /api/v1/admin/messaging/realtime/sse` opens the admin SSE fallback stream.
- `GET /api/v1/admin/messaging/realtime/ws?ticket=...` opens the admin WebSocket stream.
- `GET /api/v1/me/realtime/ws?ticket=...` opens the customer WebSocket stream.

## Routing Contract

Each authenticated principal is bound to exactly one channel:

- customer: `messaging:customer:{customer_id}`
- admin: `messaging:admin:{admin_id}`

Clients may send `{"type":"subscribe","channels":["self"]}` or the exact bound channel. Any other channel returns
`{"type":"error","code":"UNAUTHORIZED_CHANNEL"}` and is not subscribed. A customer connection can never subscribe to
an admin channel, and an admin connection can never subscribe to another admin/customer channel through this gateway.

## Recovery Contract

Realtime transports deliver event hints only. They do not return conversation state, message bodies, or notification
state. Clients must call the REST sync endpoint after connect, reconnect, `sync_required`, or local cursor gaps:

- customer: `GET /api/v1/me/realtime/sync?cursor={last_cursor}`
- admin: use the existing admin conversation and notification REST lists for state recovery.

The `connected`, `pong`, and `sync_required` transport messages include a `sync_cursor`. The cursor is an opaque marker
for clients to store with their last successful REST sync; the backend may change the format without client parsing.

## Presence

Presence is advisory and stored in Redis/Valkey with a TTL:

- connection keys: `messaging:presence:{principal_type}:{principal_id}:{connection_id}`
- index keys: `messaging:presence:index:{principal_type}:{principal_id}`

WebSocket `ping` messages refresh the TTL. SSE streams emit periodic `ping` events. If Redis is unavailable, the
connection remains open and REST sync remains the source of truth; the presence write fails closed to no presence
projection rather than rejecting the user.

## Payload Privacy

The realtime dispatcher removes routing metadata before delivery. Customer payloads additionally strip admin/customer
raw actor identifiers such as `assigned_admin_id`, `sender_id`, `participant_id`, `recipient_id`, and
`customer_account_id`. Message bodies are not included in realtime events; clients recover full state through REST.
