# CyberVPN Platform Foundation P2.2 Platform-Services GitOps Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live Flux reconciliation evidence pending  
**Packet:** `P2.2`  
**Primary owners:** `infra-platform` / `sre-platform`  
**Supporting owners:** `security`, `platform-architecture`

---

## 1. Packet Role

This document is the execution packet for `P2.2` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.2` exists to freeze the first non-prod workload-cluster base platform-services contract for the program:

- `Flux`-ordered reconciliation from `platform-gitops`;
- `cert-manager`;
- `trust-manager`;
- maintained operator-based `OpenBao -> Kubernetes Secret` integration;
- `kube-prometheus-stack`;
- `Loki`;
- `Tempo`;
- `Alloy` as the only target collector baseline.

Implementation note:

- this packet is being executed as a pre-launch `repo/validation` slice because live infrastructure is not available in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live `Flux` reconciliation, controller readiness, and runtime proof against the first non-prod workload cluster.

---

## 2. Current Baseline

Before this packet:

- `P1.6` froze the separate `platform-gitops` repository boundary and initial `Flux` bootstrap shape;
- `P2.1` froze the first workload-cluster id `nonprod-hetzner-hel1-core` and the cluster network substrate intent;
- no canonical scaffold existed for ordered platform-service reconciliation on the first workload cluster;
- the phased plan still used stale wording around `ingress` and `VSO`, even though the architecture had already frozen `Cilium Gateway API` as the ingress substrate and controller-based OpenBao delivery as the boundary.

Observed strengths:

- the target-state architecture already froze:
  - `Cilium Gateway API` as the in-cluster ingress substrate;
  - `cert-manager` plus `trust-manager` for internal PKI distribution;
  - `kube-prometheus-stack`, `Loki`, `Tempo`, and `Alloy` as the observability baseline;
  - `OpenBao` outside Kubernetes with JWT-authenticated access from cluster controllers.
- the OpenBao registry already froze the workload-cluster auth-mount naming model `jwt-k8s-<cluster-id>`.

Observed implementation risks:

- `P2.2` can drift into a second ingress-controller stack unless the packet explicitly refuses it;
- the OpenBao controller path can drift into stale or unmaintained upstream integrations unless the current maintained choice is frozen now;
- collector convergence can regress unless `Alloy` is explicitly rendered in both DaemonSet and OTLP-gateway modes now.

---

## 3. Canonical Decisions For P2.2

`P2.2` fixes the following decisions:

1. Base platform services on the first workload cluster are reconciled from `platform-gitops` through ordered `Flux` `Kustomization` objects.
2. `Cilium Gateway API` remains the ingress substrate; `P2.2` must not introduce a standalone ingress-controller chart.
3. `cert-manager` and `trust-manager` are the canonical certificate issuance and trust-distribution layer inside the cluster.
4. The maintained implementation choice for the frozen `OpenBao -> operator -> Kubernetes Secret` boundary is `External Secrets Operator`.
5. The archived `openbao-secrets-operator` is intentionally not used for `P2.2`.
6. `OpenBao` remains outside Kubernetes, and cluster auth continues to use the workload-cluster JWT mount `jwt-k8s-<cluster-id>`.
7. Non-prod observability baseline is:
   - `kube-prometheus-stack`
   - `Loki` monolithic
   - `Tempo` monolithic
   - `Alloy` DaemonSet
   - `Alloy` OTLP gateway Deployment
8. No secret values, CA payloads, or bootstrap tokens are committed into git as part of this packet.

---

## 4. Scope

In scope for `P2.2`:

- add a canonical helper under [infra/scripts/platform_services_bootstrap.py](../../infra/scripts/platform_services_bootstrap.py);
- render a platform-gitops-style scaffold for:
  - `clusters/nonprod-hetzner-hel1-core`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services`
- render ordered Flux `Kustomization` objects for the base platform-services wave;
- render source objects and Helm releases for:
  - `cert-manager`
  - `trust-manager`
  - `External Secrets Operator`
  - `kube-prometheus-stack`
  - `Loki`
  - `Tempo`
  - `Alloy`
- render cluster-local `OpenBao` integration objects:
  - JWT token request RBAC
  - `ClusterSecretStore`
  - `ExternalSecret`
  - `ClusterIssuer`
  - trust `Bundle`
- add unit coverage and local render smoke for the helper;
- update operator docs, phased plan wording, and residual tracking for honest `P2.2` closure.

Out of scope for the current repository slice executed in this workspace:

- live workload-cluster access or reconciliation;
- live `Flux` bootstrap against the first workload cluster;
- live `OpenBao` CA and secret material cut-in;
- live controller readiness or synthetic checks;
- production workload clusters.

---

## 5. Official Constraints

The execution of `P2.2` follows current primary-source guidance:

- Flux source and Helm reconciliation should use `OCIRepository`, `HelmRepository`, and `HelmRelease` objects as the canonical pull model;
- cert-manager should be installed once per cluster, and its `Vault` integration authenticates through the `auth.kubernetes` path;
- trust-manager currently uses `Bundle`, while upstream explicitly documents ongoing evolution toward `ClusterBundle`;
- `External Secrets Operator` provides the maintained Vault/OpenBao provider path with JWT authentication using `kubernetesServiceAccountToken`;
- the upstream `openbao-secrets-operator` repository is archived and read-only, so it is not a reasonable maintained day-1 choice for this packet;
- Grafana `Alloy` remains the collector baseline, and non-prod `Loki` plus `Tempo` may start in monolithic mode.

Primary sources:

- Flux sources and Helm reconciliation: https://fluxcd.io/docs/components/
- cert-manager Helm install: https://cert-manager.io/docs/installation/helm/
- cert-manager Vault configuration: https://cert-manager.io/v1.16-docs/configuration/vault/
- trust-manager install: https://cert-manager.io/docs/trust/trust-manager/installation/
- trust-manager API evolution note: https://cert-manager.io/announcements/2025/09/05/trust-manager-clusterbundle-future/
- External Secrets Operator Vault provider: https://external-secrets.io/latest/provider/hashicorp-vault/
- OpenBao Secrets Operator repository state: https://github.com/openbao/openbao-secrets-operator
- Grafana Alloy docs: https://grafana.com/docs/alloy/latest/
- Loki deployment modes: https://grafana.com/docs/loki/latest/fundamentals/architecture/
- Tempo deployment modes: https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/plan/deployment-modes/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.2`:

### 6.1 Helper And Tests

- [infra/scripts/platform_services_bootstrap.py](../../infra/scripts/platform_services_bootstrap.py)
- [infra/tests/test_platform_services_bootstrap.py](../../infra/tests/test_platform_services_bootstrap.py)

### 6.2 Operator Docs

- [infra/README.md](../../infra/README.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-2-platform-services-gitops/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-2-platform-services-gitops/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.2.1` Freeze Ordered Flux Reconciliation For Base Platform Services

**Goal:** stop platform-services work from drifting into unordered apply waves or controller pileups.

Deliverables:

- cluster-local `Flux` `Kustomization` objects for:
  - `platform-sources`
  - `platform-namespaces`
  - `platform-cert-manager`
  - `platform-external-secrets`
  - `platform-openbao-integration`
  - `platform-trust-manager`
  - `platform-trust-bundles`
  - `platform-kube-prometheus-stack`
  - `platform-observability-backends`
  - `platform-alloy`

Acceptance criteria:

- reconciliation ordering is explicit;
- source objects and controller waves are separated;
- the scaffold is reproducible from synthetic inputs.

### 7.2 `T2.2.2` Freeze The Maintained OpenBao Integration Path

**Goal:** keep the frozen `OpenBao -> operator -> Kubernetes Secret` boundary while using a currently maintained controller path.

Deliverables:

- `External Secrets Operator` Helm release;
- JWT token request RBAC for `external-secrets` and `cert-manager`;
- `ClusterSecretStore/openbao-shared`;
- `ClusterSecretStore/openbao-apps`;
- `ExternalSecret` objects for CA material;
- `ClusterIssuer/openbao-k8s-internal`.

Acceptance criteria:

- the workload-cluster JWT mount naming follows `jwt-k8s-<cluster-id>`;
- `OpenBao` remains outside the cluster;
- no secret values are committed into git;
- the packet explicitly records that `openbao-secrets-operator` is not used because upstream is archived and read-only.

### 7.3 `T2.2.3` Freeze The Non-Prod Observability Baseline

**Goal:** make the first cluster-local observability layer explicit before the workload cluster exists.

Deliverables:

- `kube-prometheus-stack` Helm release;
- non-prod `Loki` Helm release;
- non-prod `Tempo` Helm release;
- `Alloy` DaemonSet Helm release;
- `Alloy` OTLP gateway Helm release.

Acceptance criteria:

- collector posture is `Alloy` only;
- no `promtail` manifests appear in the scaffold;
- no standalone `otel-collector` chart appears in the scaffold;
- non-prod `Loki` and `Tempo` remain intentionally monolithic.

### 7.4 `T2.2.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any real workload cluster or `Flux` reconciliation exists.

Deliverables:

- helper unit tests;
- local render smoke;
- packet evidence pack;
- formal carry-forward residual for missing live reconciliation and controller-readiness proof.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are explicit;
- later `P2` packets may begin without pretending the first cluster platform-services layer already reconciles.

---

## 8. State-Boundary Rules

`P2.2` must keep the following invariants:

1. Desired state still belongs to `platform-gitops`, not to manual `kubectl apply` history.
2. `P2.2` must not introduce a standalone ingress-controller layer that competes with the `Cilium Gateway API` substrate frozen in `P2.1`.
3. `OpenBao` remains outside Kubernetes; cluster-local controllers authenticate through the workload-cluster JWT auth mount.
4. Operator-based secret delivery does not change the source-of-truth boundary: `OpenBao` remains the secret authority, not Kubernetes `Secret` objects or controller state.
5. Observability baseline must converge on `Alloy`, not revive `promtail` or standalone long-lived `otel-collector` assumptions.
6. CA material may be synchronized into the cluster, but the authoritative trust and issuer material stays owned by `OpenBao`.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| `P2.2` introduces a second ingress stack | platform services drift away from the frozen network substrate | packet and helper explicitly refuse a standalone ingress-controller chart |
| stale OpenBao operator choice leaks into the cluster | day-1 controller choice becomes unmaintained before launch | freeze the maintained ESO-based path and record why it is chosen |
| `OpenBao` integration is mistaken for secret source-of-truth migration | controller state could be treated as authority | packet keeps `OpenBao` as the authority and treats synced `Secret` objects as delivery artifacts only |
| collector convergence regresses | `promtail` or standalone OTEL patterns re-enter later packets | render only `Alloy` and document the DaemonSet plus OTLP gateway split |
| `P2.2` is treated as live-complete without reconciliation proof | later packets assume the first workload cluster is ready | carry forward `EX-022` until live Flux, controller, issuer, and trust evidence exist |
