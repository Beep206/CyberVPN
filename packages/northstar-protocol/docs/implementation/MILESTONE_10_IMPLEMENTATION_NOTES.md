# Milestone 10 Implementation Notes

## Scope

Milestone 10 hardens the remote/shared bridge-store path, adds the first deployment-shaped bridge topology, and closes the most important compatibility drift before any datagram work starts.

Normative behavior still comes from:

- `docs/spec/northstar_remnawave_bridge_spec_v0_1.md`
- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Decisions Recorded Here

### 1. Remote/shared bridge-store mode now requires auth at app-composition time

`apps/ns-bridge` no longer treats store-service auth as optional in remote mode.

Current rule:

- `--store-backend service` requires `--service-store-auth-token`
- `serve-store` requires a non-empty store-service auth token
- the deployment topology path reuses that token when the public bridge service talks to the internal store service

This keeps deployment-mode trust explicit without widening `ns-storage` or `ns-bridge-domain` contracts.

### 2. Internal store-service failures are redacted on the wire

The internal bridge-store service now returns a generic internal-failure message for `500` responses instead of echoing backend error strings into HTTP bodies.

Current rule:

- `401` and typed `404` cases stay specific
- internal failures stay structured but redacted
- client-side remote-store error decoding also avoids surfacing raw `5xx` bodies as application-visible detail

This is a hardening change only. It does not alter the frozen public `/v0/*` bridge contract.

### 3. Deployment-shaped bridge topology now exists as an explicit runtime path

`apps/ns-bridge` now includes a `serve-topology` path that runs:

- a local shared-durable store backend
- a separate internal store-service runtime
- a public bridge HTTP runtime that talks to that store over the authenticated service-backed path

Current constraints:

- the topology path requires a local shared-durable backend, not `--store-backend service`
- the public bridge side still fails closed on store-service health
- the topology remains non-fork and keeps fake vs HTTP Remnawave adapter selection outside bridge-domain contracts

### 4. Protocol error-code mapping is now aligned with the frozen wire registry

`ns-core::ProtocolErrorCode` and `ns-gateway-runtime` now use the frozen registry names and ids from the v0.1 wire freeze candidate.

Important implementation consequence:

- relay overload and relay prebuffer pressure now map to `FLOW_LIMIT_REACHED`
- timeout stays `IDLE_TIMEOUT`
- the old drifted names such as `SessionBusy` and `FlowControlExceeded` are gone from the runtime mapping

### 5. Accepted-relay lifetime is now reclaimed on all tested exit paths

`ns-gateway-runtime` now exposes an `ActiveRelayGuard` so accepted relay ids are released when the relay lifetime ends, without pushing carrier-specific code into `ns-session`.

Milestone 10 live coverage now asserts relay release for:

- successful bounded raw forwarding
- upstream-first clean half-close
- idle-timeout exit
- overload rejection on a second live H3 relay attempt

## No New ADR

Milestone 10 stays inside existing architecture seams:

- no bridge-domain contract widening
- no Remnawave fork
- no session-core transport ownership change
- no datagram or 0-RTT activation

That makes an implementation note sufficient.

## Deferred After Milestone 10

- a broader deployed remote/shared store backend beyond the current internal semantic HTTP service
- an end-to-end integration pass against a real upstream Remnawave deployment
- live datagram work
- further transport error and registry audit beyond the milestone-10 pass
