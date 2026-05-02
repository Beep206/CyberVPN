# CyberVPN Platform Foundation P1.5 Non-Prod Management Cluster Foundation Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.5`  
**Phase:** `P1`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `security`, `sre-platform`  
**Purpose:** record the concrete repository, validation, and operator-surface changes completed for `P1.5`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-5-nonprod-mgmt-foundation-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-5-nonprod-mgmt-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-017` as the formal reason `P1.5` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.5` result:

- dedicated non-prod management-cluster stack created at `infra/terraform/live/staging/nonprod-mgmt`;
- dedicated Hetzner/Talos node module created at `infra/terraform/modules/talos_node`;
- management-cluster firewall policy extended to support Talos nodes without SSH ingress;
- canonical `nonprod-mgmt` single-control-plane plus two-worker topology established with a reserved Kubernetes API endpoint IP;
- first-pass Talos provider resources declared for machine secrets, machine configuration apply, bootstrap, and kubeconfig retrieval;
- stack-local provider lockfile generated with stable `siderolabs/talos v0.10.1` and `hetznercloud/hcloud v1.60.1`;
- canonical bootstrap helper created at `infra/scripts/nonprod_mgmt_bootstrap.py`;
- unit tests and local bundle-render smoke added for the helper;
- root infra docs and stack-local docs updated to point to the new non-prod management-cluster path.

This packet is **not yet claimed complete** because:

- no operator-approved live `tofu apply` against real remote backend and cloud credentials has been executed in this evidence window;
- no live Talos bootstrap and kubeconfig retrieval has been executed against real nodes yet;
- no live `clusterctl` and provider-install evidence has been attached yet;
- no validated live `CAPH` components URL has been attached yet.

That is intentional. `P1.5` has completed the safe repo and validation slice first, while leaving live Hetzner/Talos bring-up under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Reusable Infrastructure Layer

- `infra/terraform/modules/talos_node`
  - added dedicated Hetzner VM module for Talos-based management-cluster nodes
  - provisions:
    - node labels
    - primary IPv4 attachment
    - optional reuse of a pre-created endpoint IP
    - delete and rebuild protection

- `infra/terraform/modules/firewall_policy`
  - extended with `enable_ssh`
  - now supports Talos nodes where SSH is intentionally disabled

### 3.2 Non-Prod Management-Cluster Stack

- `infra/terraform/live/staging/nonprod-mgmt`
  - dedicated stack for the canonical `nonprod-mgmt` management cluster
  - creates:
    - one reserved Kubernetes API endpoint IP
    - one control-plane node
    - at least two worker nodes
    - one management firewall
    - Talos bootstrap resources and sensitive outputs
  - includes `.terraform.lock.hcl` with the validated provider selections for the repo slice

### 3.3 Bootstrap Helper And Tests

- `infra/scripts/nonprod_mgmt_bootstrap.py`
  - renders:
    - `clusterctl/clusterctl.yaml`
    - `install-capi-core.sh`
    - `install-caph.sh`
    - `versions.env`
    - bootstrap bundle `README.md`

- `infra/tests/test_nonprod_mgmt_bootstrap.py`
  - validates Talos provider URLs are pinned
  - validates bundle rendering and CAPH compatibility guardrails

### 3.4 Operator Docs

- `infra/terraform/README.md`
- `infra/README.md`
- `infra/terraform/live/staging/nonprod-mgmt/README.md`

These now acknowledge the new non-prod management-cluster foundation path.

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 OpenTofu Formatting

Commands:

```bash
/tmp/opentofu-1.11.6/tofu fmt \
  -recursive \
  infra/terraform/modules/firewall_policy \
  infra/terraform/modules/talos_node \
  infra/terraform/live/staging/nonprod-mgmt
```

Result:

- formatting completed successfully

### 4.2 OpenTofu Init And Validate

Commands:

```bash
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/nonprod-mgmt init -backend=false -input=false -no-color
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/nonprod-mgmt validate -no-color
```

Result:

- initialization completed successfully with `-backend=false`
- validation completed successfully
- stack-local `.terraform.lock.hcl` was generated successfully for the validated provider selections

### 4.3 Bootstrap Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_nonprod_mgmt_bootstrap
```

Result:

- unit tests completed successfully

Coverage intent:

- Talos provider URLs are pinned in `clusterctl.yaml`
- rendered bundle includes the explicit CAPH guardrail instead of silently using `clusterctl` defaults

### 4.4 Bootstrap Helper Smoke Render

Command shape:

```bash
python infra/scripts/nonprod_mgmt_bootstrap.py render-bundle \
  --kubeconfig-path /secure/nonprod-mgmt.kubeconfig \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `clusterctl/clusterctl.yaml`
  - `install-capi-core.sh`
  - `install-caph.sh`
  - `versions.env`
  - `README.md`

### 4.5 Workspace Readiness Check For Live Management-Cluster Evidence

Observed in the current workspace on 2026-04-22:

- no `backend.hcl` is present under `infra/terraform/live/staging/nonprod-mgmt`
- no real `TF_VAR_hcloud_token` or remote-backend credentials are present for a live stack apply
- no real validated Talos Hetzner image or snapshot id is present in the workspace
- no live node outputs exist from a real `tofu apply`
- no validated live `CAPH` `infrastructure-components.yaml` URL is attached yet

Meaning:

- live `tofu init/plan/apply` cannot be executed honestly from this workspace yet
- live Talos bootstrap evidence cannot be attached yet
- live `clusterctl` and provider-install evidence cannot be attached yet
- the blocker is missing operator-provided backend config, cloud credentials, validated image input, and live provider-install input, not missing repo automation

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. `staging/nonprod-mgmt` is a separate stack from:
   - `staging/foundation`
   - `staging/openbao`
   - `staging/nats`
   - `staging/posthog`
   - `staging/edge`
   - `staging/dns`
   - `staging/control-plane`
2. the new stack does not read legacy host bootstrap state from `foundation`
3. canonical ids remain:
   - `environment = nonprod`
   - `management_cluster_id = nonprod-mgmt`
4. `clusterctl` default Hetzner provider discovery is intentionally not trusted inside the rendered bundle
5. no live infrastructure apply was executed as part of this repo/validation slice

Explicitly not changed:

- production management-cluster layout
- GitOps bootstrap
- workload-cluster creation through Cluster API
- Cilium or Gateway API substrate
- real CAPH components pinning

---

## 6. Residuals Before Packet Closure

Open residuals:

1. `remote-backend apply evidence` for the first real non-prod management-cluster stack apply is still pending.
2. `live Talos bootstrap evidence` is still pending.
3. `live talosconfig and kubeconfig retrieval evidence` is still pending.
4. `live clusterctl init evidence` is still pending.
5. `live CAPH install evidence` is still pending.
6. `live provider inventory evidence` is still pending.

These residuals block a full `P1.5 complete` claim, but they do **not** invalidate the already-completed repository and validation slice above.

---

## 7. Recommended Next Live Commands

When operator-provided `backend.hcl`, cloud credentials, and a validated Talos image exist, the first honest live sequence should be:

```bash
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt apply -var-file=terraform.tfvars
```

Then export the sensitive outputs out of band:

```bash
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt output -raw talosconfig > /secure/path/nonprod-mgmt.talosconfig
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt output -raw kubeconfig_raw > /secure/path/nonprod-mgmt.kubeconfig
```

Then render the operator bundle:

```bash
python infra/scripts/nonprod_mgmt_bootstrap.py render-bundle \
  --kubeconfig-path /secure/path/nonprod-mgmt.kubeconfig \
  --output-dir infra/artifacts/nonprod-mgmt-bootstrap
```

Finally:

```bash
bash infra/artifacts/nonprod-mgmt-bootstrap/install-capi-core.sh
export CAPH_COMPONENTS_URL=<validated infrastructure-components.yaml URL>
bash infra/artifacts/nonprod-mgmt-bootstrap/install-caph.sh
```
