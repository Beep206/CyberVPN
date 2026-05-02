# CyberVPN Platform Foundation P1.6 Platform GitOps Repository And Flux Bootstrap Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.6`  
**Phase:** `P1`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `sre-platform`, `security`  
**Purpose:** record the concrete repository, validation, and operator-surface changes completed for `P1.6`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-6-platform-gitops-and-flux-bootstrap-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-6-platform-gitops-and-flux-bootstrap-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-018` as the formal reason `P1.6` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.6` result:

- canonical helper created at `infra/scripts/platform_gitops_bootstrap.py`;
- unit tests added at `infra/tests/test_platform_gitops_bootstrap.py`;
- helper renders a standalone `platform-gitops` repository scaffold with:
  - `README.md`
  - `.gitignore`
  - `clusters/nonprod-mgmt`
  - `infrastructure/nonprod-mgmt`
  - `apps/nonprod-mgmt`
  - `bootstrap-flux-github.sh`
  - `check-nonprod-mgmt.sh`
  - `versions.env`
- bootstrap helper pins Flux `v2.8.6` and uses the GitHub SSH deploy-key path via `flux bootstrap github --token-auth=false`;
- operator docs updated to acknowledge the GitOps bootstrap helper and separate desired-state repository surface.

This packet is **not yet claimed complete** because:

- no live GitHub repository has been created or validated in this evidence window;
- no live `flux bootstrap` has been executed against the running `nonprod-mgmt` cluster;
- no live `flux check` or reconciliation evidence has been attached yet;
- no operator-approved GitHub token, owner, or repository bootstrap transcript has been attached yet.

That is intentional. `P1.6` has completed the safe repo and validation slice first, while leaving live GitHub and Flux bootstrap under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Bootstrap Helper And Tests

- `infra/scripts/platform_gitops_bootstrap.py`
  - renders:
    - `README.md`
    - `.gitignore`
    - `clusters/nonprod-mgmt/README.md`
    - `infrastructure/nonprod-mgmt/README.md`
    - `apps/nonprod-mgmt/README.md`
    - `scripts/bootstrap-flux-github.sh`
    - `scripts/check-nonprod-mgmt.sh`
    - `versions.env`

- `infra/tests/test_platform_gitops_bootstrap.py`
  - validates the rendered file set
  - validates the guarded Flux bootstrap posture:
    - GitHub mode
    - `--token-auth=false`
    - `clusters/nonprod-mgmt`
    - Flux `v2.8.6`
    - no image automation in the initial bootstrap script

### 3.2 Operator Docs

- `infra/README.md`

This now acknowledges the new GitOps bootstrap helper and the separate desired-state repository surface.

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_platform_gitops_bootstrap
```

Result:

- unit tests completed successfully

Coverage intent:

- the rendered repo contains the expected baseline files;
- the bootstrap script uses `flux bootstrap github --token-auth=false`;
- the rendered root `README.md` repeats the no-secret-values and read-only deploy-key posture.

### 4.2 Helper Render Smoke

Command shape:

```bash
python infra/scripts/platform_gitops_bootstrap.py render-repo \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `README.md`
  - `.gitignore`
  - `clusters/nonprod-mgmt/README.md`
  - `infrastructure/nonprod-mgmt/README.md`
  - `apps/nonprod-mgmt/README.md`
  - `scripts/bootstrap-flux-github.sh`
  - `scripts/check-nonprod-mgmt.sh`
  - `versions.env`

### 4.3 Workspace Readiness Check For Live GitOps Evidence

Observed in the current workspace on 2026-04-22:

- no real GitHub owner or repository bootstrap inputs are present in the current workspace
- no real `GITHUB_TOKEN` with repo admin scope is present in the session
- no live `nonprod-mgmt` kubeconfig from a real bootstrap exists in the current workspace
- no Flux CLI bootstrap transcript exists
- no live `flux check`, `flux get sources git -A`, or `flux get kustomizations -A` evidence exists

Meaning:

- live GitHub bootstrap cannot be executed honestly from this workspace yet
- live Flux bootstrap evidence cannot be attached yet
- the blocker is missing operator-provided GitHub and live-cluster inputs, not missing repo automation

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. `platform-gitops` remains a separate desired-state repository surface from `platform-monorepo`.
2. Flux is treated as the reconciler, not the desired-state source of truth.
3. `P1.6` scaffolds repository structure and bootstrap flow only; it does not fake real workload delivery manifests.
4. the bootstrap helper prefers GitHub SSH deploy-key auth over PAT-in-cluster auth.
5. no secret values are introduced into Git as part of this packet.

Explicitly not changed:

- live GitHub repository state
- live `nonprod-mgmt` cluster state
- HelmRelease or Kustomization delivery for real services
- image automation controllers
- production GitOps bootstrap

---

## 6. Residuals Blocking Full Closure

`P1.6` still requires operator-supplied live inputs before it can be declared complete:

- GitHub owner and repository bootstrap decision
- `GITHUB_TOKEN` with the required repository administration permissions
- live `nonprod-mgmt` kubeconfig from the real management cluster
- live Flux bootstrap transcript and post-bootstrap checks

These residuals are formalized as `EX-018` in the temporary exceptions register.

---

## 7. Required Live Closure Sequence

Once operator inputs are available, the remaining closure sequence is:

```bash
python infra/scripts/platform_gitops_bootstrap.py render-repo \
  --output-dir /secure/path/platform-gitops
```

Commit the rendered scaffold to the real `platform-gitops` repository, then from an operator workstation with `flux`, `kubectl`, and GitHub access:

```bash
export GITHUB_TOKEN=<bootstrap token>
export GITHUB_OWNER=<org-or-user>
export GITHUB_REPOSITORY=platform-gitops
bash /secure/path/platform-gitops/scripts/bootstrap-flux-github.sh
bash /secure/path/platform-gitops/scripts/check-nonprod-mgmt.sh
```

Expected live evidence:

- repository bootstrap transcript
- Flux controller installation evidence
- `flux check`
- `flux get sources git -A`
- `flux get kustomizations -A`
- cluster-side `flux-system` deployment evidence

---

## 8. Honest Status Statement

`P1.6` is complete as a **repository and local-validation slice**.

`P1.6` is **not** complete as a full packet because live GitHub and Flux bootstrap evidence has not yet been attached.

This residual blocks:

- `P1.6 complete`
- `P1 complete`
- `Gate B passed`

It does **not** block beginning later packets as long as `EX-018` remains explicit and no one pretends the non-prod GitOps control path is already live.
