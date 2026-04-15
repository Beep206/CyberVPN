# Milestone 3 Implementation Notes

These notes capture the smallest implementation-level clarifications needed to close milestone 3 without inventing new protocol fields.

## Manifest policy epoch and profile disablement

The frozen v0.1 manifest schema does not define a top-level `policy_epoch` field or an explicit carrier-profile `enabled` flag.
Milestone 3 therefore enforces these concerns through already-frozen surfaces instead of adding new manifest fields:

- stale policy epoch is enforced at token admission using the bridge-issued JWT `policy_epoch`
- disabled or withdrawn profiles are enforced through signed manifest membership plus endpoint/profile usability checks
- the client fails closed when the selected signed carrier profile has no usable signed endpoint mapping

This keeps the implementation aligned with the frozen manifest schema and the token-profile rules in `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`.

## Endpoint versus profile composition

Milestone 3 uses the following composition rule for the first carrier:

- endpoint `host` and `port` are the dial target
- carrier-profile `origin_host`, `origin_port`, optional `sni`, `alpn`, templates, and timing fields are the signed carrier presentation settings

This matches the current QUIC/H3-oriented runtime split and keeps session-core transport-agnostic.

## Trust-anchor rule

Manifest contents do not bootstrap their own trust.
The client verifies the manifest against bridge-pinned trust anchors first, then derives carrier configuration from the signed carrier-profile data.
