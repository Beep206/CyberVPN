# CyberVPN Platform Foundation P2.2 Platform-Services GitOps Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.2`  
**Phase:** `P2`  
**Primary owners:** `infra-platform` / `sre-platform`  
**Supporting owners:** `security`, `platform-architecture`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.2`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-2-platform-services-gitops-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-2-platform-services-gitops-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- this evidence pack currently carries `EX-022` as the formal reason `P2.2` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.2` result:

- canonical helper added at `infra/scripts/platform_services_bootstrap.py`;
- helper renders one workload-cluster platform-services scaffold for the frozen first non-prod cluster id `nonprod-hetzner-hel1-core`;
- helper renders ordered `Flux` reconciliation objects for:
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
- helper freezes the current maintained operator-based OpenBao integration path through `External Secrets Operator`;
- helper freezes the cluster-local observability baseline for `kube-prometheus-stack`, non-prod `Loki`, non-prod `Tempo`, and split-mode `Alloy`;
- operator docs and roadmap wording are updated so `P2.2` no longer describes a second ingress controller or stale `VSO` wording.

This packet is **not yet claimed complete** because:

- no live workload-cluster kubeconfig is available in this evidence window;
- no live `platform-gitops` repository handoff or `Flux` reconciliation evidence is attached yet;
- no live controller readiness evidence exists yet for `cert-manager`, `external-secrets`, `trust-manager`, `kube-prometheus-stack`, `Loki`, `Tempo`, or `Alloy`;
- no live `OpenBao` CA material or issuer readiness proof exists yet.

That is intentional. `P2.2` first closes the reproducible repo and controller-ordering slice, while leaving runtime reconciliation and readiness proof explicit.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/platform_services_bootstrap.py`
  - renders:
    - the root `P2.2` scaffold README;
    - the cluster-local `Flux` entrypoint for `nonprod-hetzner-hel1-core`;
    - the `infrastructure/nonprod-hetzner-hel1-core/platform-services` tree;
    - Flux source objects for OCI and Helm chart retrieval;
    - namespace manifests;
    - Helm releases for `cert-manager`, `External Secrets Operator`, `trust-manager`, `kube-prometheus-stack`, `Loki`, `Tempo`, and `Alloy`;
    - `OpenBao` integration objects including `ClusterSecretStore`, `ExternalSecret`, and `ClusterIssuer`;
    - an operator check script and `versions.env`.
  - freezes the maintained `OpenBao -> operator -> Kubernetes Secret` implementation path;
  - refuses to reintroduce a standalone ingress-controller chart.

- `infra/tests/test_platform_services_bootstrap.py`
  - validates scaffold rendering against synthetic inputs;
  - validates the `OpenBao` JWT mount, role, and namespace posture;
  - validates the `Alloy` DaemonSet and OTLP gateway split;
  - validates presence of the key source and trust-bundle artifacts.

### 3.2 Operator Docs And Canonical Program Records

- `infra/README.md`
  - now documents `platform_services_bootstrap.py` as the canonical `P2.2` operator surface
- `docs/plans/2026-04-21-platform-foundation-phased-implementation-plan.md`
  - now uses current wording for `P2.2`:
    - no standalone ingress controller
    - operator-based `OpenBao` integration instead of stale `VSO` wording
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-022`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_platform_services_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/platform_services_bootstrap.py
```

Result:

- compilation completed successfully

### 4.3 Helper Smoke Render

Command shape:

```bash
python infra/scripts/platform_services_bootstrap.py render-scaffold \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `README.md`
  - `clusters/nonprod-hetzner-hel1-core/README.md`
  - `clusters/nonprod-hetzner-hel1-core/kustomization.yaml`
  - `clusters/nonprod-hetzner-hel1-core/platform-sources.yaml`
  - `clusters/nonprod-hetzner-hel1-core/platform-openbao-integration.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/README.md`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/versions.env`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/sources/external-secrets-repository.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/openbao-integration/clustersecretstore-openbao-shared.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/openbao-integration/clusterissuer-openbao-internal.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/alloy/daemonset-helmrelease.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/platform-services/alloy/otlp-gateway-helmrelease.yaml`
  - `scripts/check-platform-services.sh`

### 4.4 Workspace Readiness Check For Live Reconciliation Evidence

Observed in the current workspace on 2026-04-22:

- no live workload-cluster kubeconfig is present in the current session;
- no real `platform-gitops` repository or cluster path handoff is attached in the current session;
- no `Flux` bootstrap or reconciliation evidence exists in this workspace for the first workload cluster;
- no live `OpenBao` CA material or runtime controller evidence exists in this session;
- no live workload-cluster monitoring or trust-distribution evidence is present in this workspace.

Meaning:

- the packet cannot honestly claim live `Flux` reconciliation yet;
- the packet cannot honestly claim runtime controller readiness yet;
- `P2.2` must therefore carry a formal residual until those steps are executed against the real non-prod workload cluster.

---

## 5. Remaining Live Closure Requirements

`P2.2` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. a real `platform-gitops` repository contains the rendered `P2.2` cluster and infrastructure paths;
2. real `Flux` reconciliation evidence exists for:
   - `platform-sources`
   - `platform-cert-manager`
   - `platform-external-secrets`
   - `platform-openbao-integration`
   - `platform-trust-manager`
   - `platform-trust-bundles`
   - `platform-kube-prometheus-stack`
   - `platform-observability-backends`
   - `platform-alloy`
3. live controller readiness evidence exists for:
   - `cert-manager`
   - `external-secrets`
   - `kube-prometheus-stack`
   - `loki`
   - `tempo`
   - `alloy-daemonset`
   - `alloy-otlp-gateway`
4. live `OpenBao` integration evidence exists for:
   - `ClusterSecretStore/openbao-shared`
   - `ClusterSecretStore/openbao-apps`
   - `ExternalSecret/openbao-server-ca`
   - `ExternalSecret/openbao-k8s-ca`
   - `ClusterIssuer/openbao-k8s-internal`
   - `Bundle/openbao-k8s-internal-ca`
5. an explicit operator record exists that `P2.2` introduced no standalone ingress controller and continues to rely on the `Cilium Gateway API` substrate frozen in `P2.1`.
