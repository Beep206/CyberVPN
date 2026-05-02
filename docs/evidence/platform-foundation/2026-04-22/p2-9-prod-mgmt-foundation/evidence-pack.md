# CyberVPN Platform Foundation P2.9 Production Management Cluster Foundation Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.9`  
**Phase:** `P2`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `sre-platform`, `security`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.9`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-9-prod-mgmt-foundation-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-9-prod-mgmt-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` cannot be claimed because `P2.1` through `P2.9` still carry live-closure exceptions.
- this evidence pack carries `EX-029` as the formal reason `P2.9` may remain in progress while later work continues.

---

## 2. Result Snapshot

Current `P2.9` result:

- dedicated production management-cluster stack created at `infra/terraform/live/production/prod-mgmt`;
- canonical `prod-mgmt` topology frozen as:
  - at least three control-plane nodes
  - at least two worker nodes
  - one provider-native Hetzner L4 load balancer for the stable Kubernetes API endpoint;
- first-pass Talos provider resources declared for machine secrets, machine configuration apply, bootstrap, and kubeconfig retrieval;
- stack-local provider lockfile generated with stable `siderolabs/talos v0.10.1` and `hetznercloud/hcloud v1.60.1`;
- canonical bootstrap helper created at `infra/scripts/prod_mgmt_bootstrap.py`;
- unit tests and local bundle-render smoke added for the helper;
- root infra docs and stack-local docs updated to point to the new production management-cluster foundation path.

This packet is **not yet claimed complete** because:

- no operator-approved live `tofu apply` against real remote backend and cloud credentials has been executed in this evidence window;
- no live Kubernetes API load-balancer health evidence has been executed against real nodes yet;
- no live Talos bootstrap and kubeconfig retrieval has been executed against real nodes yet;
- no live `clusterctl` and provider-install evidence has been attached yet;
- no validated live `CAPH` `infrastructure-components.yaml` URL has been attached yet.

That is intentional. `P2.9` has completed the safe repo and validation slice first, while leaving live production bring-up under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Production Management-Cluster Stack

- `infra/terraform/live/production/prod-mgmt`
  - dedicated stack for the canonical `prod-mgmt` management cluster
  - creates:
    - one Hetzner load balancer for the stable Kubernetes API endpoint
    - at least three control-plane nodes
    - at least two worker nodes
    - one management firewall
    - Talos bootstrap resources and sensitive outputs
  - includes `.terraform.lock.hcl` with the validated provider selections for the repo slice

### 3.2 Bootstrap Helper And Tests

- `infra/scripts/prod_mgmt_bootstrap.py`
  - renders:
    - `clusterctl/clusterctl.yaml`
    - `install-capi-core.sh`
    - `install-caph.sh`
    - `versions.env`
    - bootstrap bundle `README.md`

- `infra/tests/test_prod_mgmt_bootstrap.py`
  - validates Talos provider URLs are pinned
  - validates bundle rendering and production notes for the provider-native L4 endpoint posture

### 3.3 Operator Docs

- `infra/terraform/README.md`
- `infra/README.md`
- `infra/terraform/live/production/prod-mgmt/README.md`

These now acknowledge the new production management-cluster foundation path.

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/prod_mgmt_bootstrap.py
```

Result:

- compilation completed successfully

### 4.2 Bootstrap Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_prod_mgmt_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

Coverage intent:

- Talos provider URLs are pinned in `clusterctl.yaml`
- rendered bundle includes the explicit CAPH guardrail and production endpoint notes

### 4.3 Bootstrap Helper Smoke Render

Command shape:

```bash
python infra/scripts/prod_mgmt_bootstrap.py render-bundle \
  --kubeconfig-path /secure/path/prod-mgmt.kubeconfig \
  --output-dir /tmp/prod-mgmt-bootstrap-smoke
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `clusterctl/clusterctl.yaml`
  - `install-capi-core.sh`
  - `install-caph.sh`
  - `versions.env`
  - `README.md`

### 4.4 OpenTofu Formatting

Command:

```bash
/tmp/opentofu-1.11.6/tofu fmt -recursive infra/terraform/live/production/prod-mgmt
```

Result:

- formatting completed successfully

### 4.5 OpenTofu Init And Validate

Commands:

```bash
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/production/prod-mgmt init -backend=false -input=false -no-color
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/production/prod-mgmt validate -no-color
```

Result:

- initialization completed successfully with `-backend=false`
- validation completed successfully
- stack-local `.terraform.lock.hcl` was generated successfully for the validated provider selections

### 4.6 Workspace Readiness Check For Live Production Evidence

Observed in the current workspace on 2026-04-22:

- no `backend.hcl` is present under `infra/terraform/live/production/prod-mgmt`
- no real `TF_VAR_hcloud_token` or remote-backend credentials are present for a live stack apply
- no real validated Talos Hetzner image or snapshot id is present in the workspace
- no live node outputs exist from a real `tofu apply`
- no live Hetzner load-balancer health or target-attachment evidence exists yet
- no validated live `CAPH` `infrastructure-components.yaml` URL is attached yet

Meaning:

- live `tofu init/plan/apply` cannot be executed honestly from this workspace yet
- live production load-balancer evidence cannot be attached yet
- live Talos bootstrap evidence cannot be attached yet
- live `clusterctl` and provider-install evidence cannot be attached yet
- the blocker is missing operator-provided backend config, cloud credentials, validated image input, production change approval, and live provider-install input, not missing repo automation

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. `production/prod-mgmt` is a separate stack from:
   - `production/foundation`
   - `production/edge`
   - `production/dns`
   - `production/control-plane`
   - all `staging/*` non-prod stacks
2. the new stack does not read legacy host bootstrap state from `foundation`
3. canonical ids remain:
   - `environment = prod`
   - `management_cluster_id = prod-mgmt`
4. the provider-native L4 endpoint belongs only to this stack
5. `clusterctl` default Hetzner provider discovery is intentionally not trusted inside the rendered bundle
6. no live infrastructure apply was executed as part of this repo/validation slice

Explicitly not changed:

- production workload-cluster creation
- production GitOps bootstrap
- Cilium or Gateway API substrate for production workloads
- Cloudflare workload-edge mappings
- real CAPH components pinning

---

## 6. Remaining Live Closure Requirements

`P2.9` can only move from "repo slice complete" to "packet complete" when the following evidence exists:

1. remote-backend apply evidence for the first real production management-cluster stack apply;
2. live Hetzner load-balancer endpoint and health evidence for the Kubernetes API;
3. live Talos bootstrap evidence;
4. live `talosconfig` and `kubeconfig` retrieval evidence;
5. live `clusterctl init` evidence on the production management cluster;
6. live CAPH install evidence using an explicitly validated manifest URL;
7. `EX-029` is removed from the exceptions register.
