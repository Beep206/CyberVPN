# Helix Protocol Agility

## Goal and Scope

This document defines how CyberVPN's Helix must stay adaptable when network filtering, fingerprint pressure, or transport-specific blocking behavior changes.

The goal is not to make the transport “hard to block once”. The goal is to make the platform *fast to adapt repeatedly* without a long, risky rewrite cycle.

This document is public-safe inside the repository. Sensitive resilience mechanisms, fingerprint-evasion specifics, and blocking-response tactics still belong only in restricted internal materials.

## Fixed Constraints

- `Remnawave` remains authoritative for users, subscriptions, plans, billing entitlements, and base node inventory.
- Phase one remains `desktop-only`.
- The architecture remains `adapter + node daemon + backend facade + desktop runtime`.
- Existing `xray` and `sing-box` recovery paths remain mandatory.
- Anti-blocking specifics stay out of general docs and code comments.

## Agility Model

### 1. Data-First Adaptation

The transport must be changeable through versioned control-plane data before requiring binary replacement.

That means the system should prefer:

- manifest profile rotation;
- policy version updates;
- route and path policy changes;
- capability-aware assignment changes;
- staged rollout and revoke.

Binary updates are still allowed, but they should be reserved for:

- new capability families;
- cryptographic or runtime primitives not already supported by the sidecar;
- security defects that cannot be mitigated by policy rotation alone.

### 2. Stable Outer Contract, Evolving Inner Profiles

The control-plane contracts should stay stable while the transport behavior evolves through versioned profiles.

The practical rule is:

- backend and desktop ask for a manifest;
- the manifest references a transport profile and policy version;
- the desktop/runtime decides whether it already supports that profile family;
- the adapter selects only compatible profiles for the current desktop and node capability set.

This keeps most transport evolution inside profile selection and rollout control rather than inside app-wide rewrites.

### 3. Capability Negotiation Must Be Real

Desktop and node daemons must advertise capability families, not just a single protocol version number.

The adapter should be able to answer:

- which profile families the desktop build supports;
- which runtime features the node daemon supports;
- which profiles are safe to issue for a given rollout channel;
- which older profiles remain valid as fallback during migration.

### 4. Parallel Compatibility Windows

The system must support controlled overlap between:

- current active profile;
- candidate replacement profile;
- last-known-good compatible profile.

This overlap is what makes fast adaptation realistic. Without it, every blocking event turns into a synchronized cutover risk.

## Control-Plane Impact

The adapter should evolve toward a profile-driven model with:

- `transport_profile_id`
- `transport_profile_version`
- `policy_version`
- `compatibility_window`
- `deprecation_state`

These semantics should be represented in shared contracts before desktop and node integration harden around v1-only assumptions.

The adapter must also support:

- emergency profile deny or revoke;
- channel-scoped profile promotion;
- compatibility filtering based on desktop and node capabilities;
- auditability for which profile was issued to which client and rollout.

## Runtime Impact

### Desktop

The desktop sidecar should be designed to:

- accept profile-driven runtime inputs;
- load supported profile families from local capabilities;
- reject incompatible profiles safely;
- fall back to a stable core when the candidate profile is unsupported or unhealthy.

### Node

The node daemon should be designed to:

- keep last-known-good bundle references by profile version;
- apply candidate profiles atomically;
- allow controlled overlap during profile migration;
- roll back to a compatible prior profile without disrupting baseline transports.

## Performance and Resilience Impact

Agility is not only a censorship-resilience feature. It is also a product-speed feature.

If we do this correctly:

- we can respond to breakage faster;
- we can isolate risky changes to `lab` or `canary`;
- we can benchmark new profile generations against `VLESS` and `XHTTP` before promotion;
- we can avoid shipping a “fixed” binary when a profile or policy update is enough.

## Failure Modes and Recovery

The system should assume some adaptation attempts will fail.

Required response shape:

- revoke bad profile issuance quickly;
- stop promotion of the affected profile family;
- keep compatible previous profiles available during the rollback window;
- restore desktop users to stable cores if Helix health drops.

## Observability Requirements

We need first-class evidence for protocol agility, not just connection success.

Track at minimum:

- manifest issuance by `transport_profile_id`;
- connect success by profile family;
- fallback rate by profile family;
- rollback count by profile family;
- profile revoke propagation time;
- profile mismatch or incompatibility rejects.

## Immediate Design Implications

Before desktop and node integration go much further, we should treat the following as mandatory next-step contract work:

1. add profile and policy version semantics to manifest and node-assignment contracts;
2. add explicit capability-family negotiation to desktop and node contracts;
3. add profile compatibility filtering inside the adapter;
4. keep emergency revoke and stable fallback wired as the safety boundary.

## Final Rule

If a future transport change requires coordinated code rewrites across adapter, backend, node daemon, and desktop for a config-only adaptation, that is a design smell and should be treated as an architecture defect.
