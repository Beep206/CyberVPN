# Helix Compatibility Matrix

## Purpose

This matrix defines the support envelope for the Helix during the first implementation wave. It separates required validation from deferred support so the team does not accidentally over-promise compatibility.

## Desktop Client Matrix

| Platform | Architecture | Phase 1 Status | Canary Eligibility | Notes |
|---|---|---|---|---|
| Windows 11 | x64 | Required | Yes | Primary desktop validation target |
| Windows 10 | x64 | Required | Yes | Secondary production target |
| macOS 14 | arm64 | Lab-only | Later | Runtime packaging and signing required |
| macOS 15 | arm64 | Lab-only | Later | Promote only after lab stability |
| Ubuntu 22.04 | x64 | Lab-only | Later | Engineering validation target |
| Ubuntu 24.04 | x64 | Lab-only | Later | Engineering validation target |
| Windows 11 | arm64 | Deferred | No | Out of first implementation wave |
| Other Linux desktop distributions | Deferred | No | Explicitly unsupported in phase one |

## Node Matrix

| Node Class | OS | Status | Notes |
|---|---|---|---|
| Lab node | Linux x64 | Required | First daemon and rollback validation target |
| Prod-like node | Linux x64 | Required | Used before real canary |
| Regional production node | Linux x64 | Required | Canary and stable target |
| Mixed-purpose node with fragile custom ops | Conditional | No by default | Requires SRE approval before enablement |
| Non-Linux node | Unsupported | No | Out of scope for phase one |

## Rollout Channel Matrix

| Channel | Desktop Builds | Node Groups | Benchmark Requirement | User Exposure |
|---|---|---|---|---|
| `lab` | Engineering and internal test builds | `lab` only | Required | Internal only |
| `canary` | Signed internal desktop builds | `prod-like`, selected `regional` | Required and green | Internal users only |
| `stable` | Signed release builds | selected `regional` groups | Required and green | Allowed only after canary exit |

## Manifest and Runtime Compatibility Rules

- Desktop must reject manifests whose `protocol_version` is unsupported by the client.
- Node daemon must reject assignments that require a newer minimum daemon version than it currently runs.
- Adapter must not issue a manifest to a desktop client whose declared capability profile does not satisfy manifest requirements.
- Rollout publication must target only nodes and clients that satisfy the compatibility rules above.

## Explicit Exclusions For Phase One

- Mobile clients
- Browser extension clients
- Android TV client
- Non-versioned desktop manifests
- Nodes that cannot support isolated daemon file paths, ports, and rollback state directories
