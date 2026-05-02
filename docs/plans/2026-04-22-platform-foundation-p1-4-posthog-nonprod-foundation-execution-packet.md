# CyberVPN Platform Foundation P1.4 PostHog Non-Prod Foundation Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live apply/bootstrap evidence pending  
**Packet:** `P1.4`  
**Primary owners:** `infra-platform` / `growth-platform`  
**Supporting owners:** `platform-architecture`, `security`, `sre-platform`

---

## 1. Packet Role

This document is the execution packet for `P1.4` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md](../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md)
- [../growth-platform/posthog-feature-flag-governance.md](../growth-platform/posthog-feature-flag-governance.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.4` exists to establish the first canonical non-prod `PostHog` control plane for the program:

- external to Kubernetes;
- canonical environment id `nonprod`;
- canonical instance id `posthog-nonprod`;
- dedicated Linux VM with Docker-based self-host stack;
- host-level `NGINX` reverse proxy in front of the self-host services;
- baseline local backup path and protected UI access posture.

Implementation note:

- the repository slice for this packet is already implemented and locally validated;
- the remaining closure work is focused on live stack apply evidence, live bundle installation evidence, real reverse-proxy/TLS evidence, capture/flag smoke evidence, and operator-supplied backend/cloud/domain inputs.

---

## 2. Current Baseline

Before this packet:

- the repository had no canonical `PostHog` stack under [infra/terraform/live](../../infra/terraform/live);
- target-state `PostHog` placement, privacy, and flag-governance posture existed only at the documentation layer;
- the repo still contains local dev-only flags and runtime telemetry paths that are explicitly not the target production analytics plane;
- no dedicated non-prod product-intelligence host existed for later SDK, server-side capture, or experiment rollout work.

Observed strengths:

- `T0.4` already froze the product taxonomy, blocked-property list, and feature-flag governance;
- `P1.1` already established `OpenTofu` as the canonical IaC engine;
- current Hetzner and remote-state patterns already exist in the repo;
- current packet discipline already treats `PostHog` as separate from observability and source-of-truth business state.

Observed implementation risks:

- a new `PostHog` stack can drift back into legacy `staging` vocabulary unless canonical ids are repeated everywhere;
- relying on the default hobby `proxy` as the public ingress would create an avoidable proxy chain and blur trusted-proxy posture;
- privacy constraints can be violated quickly if self-host deployment happens before explicit source-of-capture and blocked-property governance are enforced;
- “zero license cost” can be misread as “no ops cost” unless deployment, access control, and backup posture are spelled out.

---

## 3. Canonical Decisions For P1.4

`P1.4` fixes the following decisions:

1. `PostHog self-hosted` remains outside Kubernetes on a dedicated VM.
2. The first implementation path is `infra/terraform/live/staging/posthog`, but the canonical environment id inside the stack is `nonprod`.
3. The canonical instance id is `posthog-nonprod`.
4. The non-prod baseline is a single dedicated VM.
5. The public ingress is host-level `NGINX`, not the hobby compose `proxy` container.
6. The Docker stack runs on localhost-bound service ports and the compose `proxy` service is intentionally excluded from the public path.
7. `PostHog` is deployed as product analytics, product-facing flags, and experiments only; it is not operational observability and not business source of truth.
8. The bundle renderer is responsible for env, proxy, protected UI access, and baseline local backup script generation.
9. Session replay remains off by default and uncontrolled autocapture remains out of bounds for production posture.
10. The backup posture in this packet is local baseline only; real backup/restore conformance remains a later packet concern.

---

## 4. Scope

In scope for `P1.4`:

- add a dedicated `PostHog` VM module under [infra/terraform/modules/posthog_node](../../infra/terraform/modules/posthog_node);
- add a non-prod implementation stack under [infra/terraform/live/staging/posthog](../../infra/terraform/live/staging/posthog);
- create a canonical `posthog-nonprod` single-node baseline with firewall and remote-state boundary;
- add pinned cloud-init bootstrap for Docker, Docker Compose, `NGINX`, `certbot`, and baseline local backup timer;
- add a canonical bootstrap helper under [infra/scripts/posthog_bootstrap.py](../../infra/scripts/posthog_bootstrap.py);
- add unit coverage and local render smoke for the bootstrap helper;
- update operator docs and evidence path for the new non-prod foundation.

Out of scope for `P1.4`:

- production `PostHog`;
- HA or multi-node PostHog;
- final object-storage or off-host backup posture;
- actual frontend SDK rollout or server-side capture implementation;
- authoritative analytics bridge from `NATS`;
- experiment or feature-flag code integration in apps;
- privacy sign-off for new event sources beyond the already frozen baseline.

---

## 5. Official Constraints

The execution of `P1.4` must follow the current official `PostHog` guidance:

- self-host deployments are supported through the single-instance hobby Docker path rather than Kubernetes;
- self-host posture is data-intensive enough to require a dedicated Linux VM with meaningful CPU/RAM/storage, not a sidecar on a random control-plane box;
- production proxying must explicitly distinguish public ingest endpoints from protected UI and must document proxy awareness and trusted-proxy behavior;
- client-side feature flags and product analytics are not infrastructure control surfaces;
- privacy controls remain application responsibilities even when self-hosting.

Primary sources:

- Self-host overview: https://posthog.com/docs/self-host
- Hobby deploy guidance: https://posthog.com/docs/self-host/deploy/hobby
- Running behind proxy: https://posthog.com/docs/self-host/configure/running-behind-proxy
- Privacy: https://posthog.com/docs/privacy
- Session replay privacy: https://posthog.com/docs/session-replay/privacy

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.4`:

### 6.1 Infrastructure Modules And Stacks

- [infra/terraform/modules/posthog_node](../../infra/terraform/modules/posthog_node)
- [infra/terraform/live/staging/posthog](../../infra/terraform/live/staging/posthog)

### 6.2 Bootstrap Assets And Tests

- [infra/scripts/posthog_bootstrap.py](../../infra/scripts/posthog_bootstrap.py)
- [infra/tests/test_posthog_bootstrap.py](../../infra/tests/test_posthog_bootstrap.py)

### 6.3 Operator Docs

- [infra/terraform/README.md](../../infra/terraform/README.md)
- [infra/README.md](../../infra/README.md)
- [infra/terraform/live/staging/posthog/README.md](../../infra/terraform/live/staging/posthog/README.md)

---

## 7. Workboard

### 7.1 `T1.4.1` Provision The Non-Prod Stack Boundary

**Goal:** create one clean, isolated state object for the non-prod `PostHog` foundation.

Deliverables:

- dedicated stack under `live/staging/posthog`;
- explicit outputs for node access and canonical domain;
- separate state boundary from `foundation`, `openbao`, `nats`, `edge`, and legacy `control-plane`.

Acceptance criteria:

- the stack validates independently under `tofu`;
- it reads shared SSH key names from `foundation` only;
- it does not merge itself into legacy control-plane state.

### 7.2 `T1.4.2` Bootstrap A Safe External PostHog Host

**Goal:** make first boot predictable and non-ad hoc.

Deliverables:

- pinned host bootstrap for Docker, Docker Compose, `NGINX`, and `certbot`;
- dedicated install path under `/opt/posthog/self-host`;
- baseline local backup timer and backup script.

Acceptance criteria:

- no secrets or generated credentials are written into git-tracked Terraform inputs;
- operator-created bundle install is the only supported start path;
- the host bootstraps the packages and directories needed for a controlled self-host deployment.

### 7.3 `T1.4.3` Freeze The Baseline Env, Proxy, And Protected UI Flow

**Goal:** stop deployment and ingress drift before later packets depend on them.

Deliverables:

- bootstrap helper that renders env, compose override, proxy config, backup script, and install script;
- protected UI catch-all with explicit public-ingest path exceptions;
- baseline generated credentials manifest.

Acceptance criteria:

- the helper renders a reproducible bundle from explicit inputs;
- the helper does not require hand-edited ad hoc shell snippets;
- the generated output is obviously marked as sensitive and kept outside git.

### 7.4 `T1.4.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live PostHog evidence.

Deliverables:

- `tofu validate` on the new stack;
- unit tests and local render smoke for the bootstrap helper;
- packet evidence pack documenting what is done and what still requires operator-provided credentials, DNS, and domain inputs.

Acceptance criteria:

- local repo slice is validated;
- residuals are written explicitly;
- later packets may begin without pretending that live PostHog evidence already exists.

---

## 8. State-Boundary Rules

`P1.4` must keep the following invariants:

1. `staging/posthog` is its own remote state object.
2. `staging/posthog` may read `staging/foundation` through remote state for SSH key names only.
3. `staging/posthog` must not write into legacy `foundation`, `openbao`, `nats`, `edge`, `dns`, or `control-plane` state.
4. The stack path may remain under legacy `staging/`, but the canonical environment id in resource names and labels remains `nonprod`.
5. No application workload may claim PostHog readiness until real capture and feature-flag smoke evidence exists.
6. Privacy and flag-governance baselines remain authoritative and are not relaxed by infrastructure convenience.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| hobby proxy becomes the public edge by accident | proxy awareness and access control become ambiguous | keep host-level `NGINX` as public ingress and treat hobby `proxy` as not part of the public path |
| generated PostHog secrets or basic-auth credentials leak into git | product-intelligence surface starts insecurely | render bundles out of band and treat output directories as sensitive |
| uncontrolled capture becomes “easy” because PostHog is live | privacy posture is violated before product contracts are implemented | keep infrastructure separate from event-taxonomy rollout and require `T0.4` rules |
| local backup script is mistaken for full DR posture | later recovery claims become misleading | document baseline backup as local-only and defer full restore conformance to later packets |
| non-prod UI is left wide open | analytics/admin plane gets unnecessary exposure | protect catch-all UI path with admin allowlists and basic auth |

---

## 10. Exit Criteria

`P1.4` is complete only when all of the following are true:

1. The dedicated `PostHog` stack validates under `OpenTofu`.
2. The non-prod `PostHog` VM module, stack, bootstrap helper, and docs exist in the repository.
3. Operator docs point to the new stack and bootstrap helper.
4. A real non-prod stack apply has been executed against a real backend and cloud credentials.
5. The rendered bootstrap bundle has been installed on the live host.
6. Live evidence exists for:
   - `NGINX` proxy serving the configured domain;
   - TLS on the configured domain;
   - login to the protected UI path;
   - capture or identify smoke through the public ingest path;
   - baseline backup script execution.

Until then, `P1.4` may be described only as:

- repository slice implemented;
- local validation complete;
- live non-prod cut-in pending.
