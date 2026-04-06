# Helix Threat Model

## Goal And Scope

Этот threat model покрывает `Helix` как desktop-first transport stack:

- `services/helix-adapter`
- `services/helix-node`
- `backend/src/presentation/api/v1/helix`
- `apps/desktop-client/src-tauri/src/engine/helix`
- `packages/helix-runtime`

Фокус: internal beta и ближайший путь к production desktop rollout.

## Fixed Constraints

- `Remnawave` остаётся источником истины для пользователей, подписок, entitlements и node inventory.
- transport-specific state живёт только в `Helix` adapter tables и runtime state.
- Desktop всегда должен иметь fallback на stable cores.
- node daemon всегда должен поддерживать last-known-good restore.
- sensitive transport internals не должны утекать в публичную документацию.

## Trust Boundaries

1. Desktop user session ↔ backend authenticated facade
2. backend / worker / node ↔ adapter internal auth boundary
3. adapter ↔ PostgreSQL service-owned Helix schema
4. desktop runtime ↔ node runtime transport session
5. operator / admin workflows ↔ canary and rollout control surfaces

## Assets

- manifest signing key / seed
- adapter internal auth token
- node bootstrap credentials
- Desktop runtime tokens and support bundles
- rollout policy state
- canary evidence and benchmark evidence
- last-known-good runtime bundles

## Main Threats

### 1. Unauthorized Internal Control Access

Risk:
- attacker or misconfigured service reaches adapter internal endpoints and forges rollout, manifest, or evidence actions

Mitigations:
- rotate `HELIX_ADAPTER_INTERNAL_TOKEN`
- never expose adapter admin/internal routes publicly
- backend and worker remain the public/authenticated façade

### 2. Manifest Signing Compromise

Risk:
- forged manifests accepted by Desktop or nodes

Mitigations:
- separate manifest signing secret from other app secrets
- short manifest lifetime
- explicit rotation procedure
- do not widen rollout during signing rotation

### 3. Runtime Bundle Or Assignment Corruption

Risk:
- bad bundle reaches node and destabilizes runtime

Mitigations:
- health-gated apply
- automatic rollback to last-known-good
- rollback drills before wider canary exposure

### 4. Canary Evidence Poisoning

Risk:
- synthetic or malformed runtime evidence distorts canary decisions

Mitigations:
- typed runtime event contracts
- backend-authenticated event path
- formal canary evidence snapshot as single source of truth
- worker reacts to snapshot, not to ad-hoc heuristics

### 5. Sensitive Data Leakage In Support Bundles

Risk:
- logs or support bundles contain long-lived secrets, tokens, or sensitive runtime internals

Mitigations:
- redact support exports
- keep support bundle scope narrow
- audit exported fields during internal beta

### 6. Operational Misuse During Incident Response

Risk:
- operator resumes rollout too early or rotates profile without confirming convergence

Mitigations:
- explicit rollback drill
- canary control follow-up actions
- internal beta checklist
- named admin / ops / sre ownership on rollout gates

## Fail-Open / Fail-Closed Rules

- manifest issuance for unstable `Helix` profiles should fail closed for new Helix sessions
- Desktop connection UX should fail open to stable cores
- node runtime should fail closed to last-known-good bundle
- canary promotion should fail closed on evidence gaps

## Internal Beta Security Requirements

- adapter internal token rotation documented and tested
- manifest signing rotation documented
- rollback drill passes at least once
- support bundles reviewed for sensitive leakage
- canary evidence remains readable during runtime-event load

## Remaining Risks Before Production

- long-run live evidence poisoning and noisy desktop cohorts
- key rotation mistakes during real operator workflows
- route churn under hostile or highly unstable real networks
- support process quality during the first incident wave
