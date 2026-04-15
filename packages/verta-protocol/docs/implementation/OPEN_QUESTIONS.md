# Verta Open Questions

These are the main implementation ambiguities that surfaced during bootstrap.
They do not block the first baseline, but they must remain visible.

## Manifest signature input canonicalization

- Resolved for the reference implementation by `docs/adr/0001-manifest-signing-reference-profile.md`.
- Follow-up action: fold the same profile into the normative spec set if the project wants this exact representation to be the long-term interoperability rule.

## Refresh credential representation

- The bridge spec allows hashed opaque secrets, references to externally managed credentials, or signed tokens with revocation handles.
- Baseline action: use hashed opaque refresh credentials in the reference bridge path and keep the type shape open for rotation later.

## Webhook replay cache storage

- The threat model requires replay protection for signed webhooks, and milestone 3 now enforces verified-delivery dedupe in the bridge-domain path.
- Remaining question: what durable, cross-process replay semantics should production bridge deployments guarantee beyond the current in-memory store?

## Carrier bootstrap depth

- The workspace plan clearly requires QUIC/H3 as the first carrier, but the minimum acceptable wire-up for the first compile-ready milestone is still a judgment call.
- Baseline action: ship config mapping, trait boundaries, and builder scaffolding now; leave full live H3 session establishment as the next milestone once core/session/auth/bridge flows are stable.

## Manifest policy epoch representation

- The frozen manifest schema does not contain a top-level `policy_epoch` or explicit carrier-profile enable flag.
- Milestone-3 action: keep stale-policy enforcement in token admission and keep disabled-profile handling in signed profile membership plus endpoint availability; see `docs/implementation/MILESTONE_3_IMPLEMENTATION_NOTES.md`.
