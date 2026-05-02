# CyberVPN Platform Foundation P1.4 PostHog Non-Prod Foundation Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.4`  
**Phase:** `P1`  
**Primary owners:** `infra-platform` / `growth-platform`  
**Supporting owners:** `platform-architecture`, `security`, `sre-platform`  
**Purpose:** record the concrete repository, validation, and operator-surface changes completed for `P1.4`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-4-posthog-nonprod-foundation-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-4-posthog-nonprod-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-016` as the formal reason `P1.4` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.4` result:

- dedicated non-prod `PostHog` stack created at `infra/terraform/live/staging/posthog`;
- dedicated Hetzner VM module created at `infra/terraform/modules/posthog_node`;
- canonical `posthog-nonprod` single-node topology established with host bootstrap for Docker, Docker Compose, `NGINX`, `certbot`, and a baseline local backup timer;
- canonical bootstrap helper created at `infra/scripts/posthog_bootstrap.py`;
- unit tests and local bundle-render smoke added for the bootstrap helper;
- root infra docs and stack-local docs updated to point to the new non-prod foundation path.

This packet is **not yet claimed complete** because:

- no operator-approved live `tofu apply` against real remote backend and cloud credentials has been executed in this evidence window;
- no live bundle installation has been executed on a real host yet;
- no live domain, `NGINX`, TLS, login, capture, or backup smoke evidence has been attached yet.

That is intentional. `P1.4` has completed the safe repo and validation slice first, while leaving live product-intelligence bring-up under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Reusable Infrastructure Layer

- `infra/terraform/modules/posthog_node`
  - added dedicated Hetzner VM module for external `PostHog`
  - provisions:
    - primary IPv4
    - cloud-init bootstrap
    - pinned host package install path for Docker, Compose, `NGINX`, and `certbot`
    - baseline local backup timer
    - bootstrap metadata for out-of-band bundle installation

### 3.2 Non-Prod PostHog Stack

- `infra/terraform/live/staging/posthog`
  - dedicated stack for the canonical `posthog-nonprod` foundation
  - creates:
    - one dedicated PostHog host
    - PostHog firewall
  - reads only the legacy `staging/foundation` SSH key registry through remote state

### 3.3 Bootstrap Helper And Tests

- `infra/scripts/posthog_bootstrap.py`
  - renders:
    - deployment `.env`
    - compose override file with localhost-only service bindings
    - HTTP and HTTPS `NGINX` configs
    - baseline local backup script
    - install script
    - generated credentials manifest

- `infra/tests/test_posthog_bootstrap.py`
  - validates env rendering defaults
  - validates bundle output structure

### 3.4 Operator Docs

- `infra/terraform/README.md`
- `infra/README.md`
- `infra/terraform/live/staging/posthog/README.md`

These now acknowledge the new non-prod `PostHog` foundation path.

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 OpenTofu Formatting

Command:

```bash
/tmp/opentofu-1.11.6/tofu fmt -recursive \
  infra/terraform/modules/posthog_node \
  infra/terraform/live/staging/posthog
```

Result:

- formatting completed successfully

### 4.2 OpenTofu Init And Validate

Commands:

```bash
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/posthog init -backend=false -input=false -no-color
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/posthog validate -no-color
```

Result:

- initialization completed successfully with `-backend=false`
- validation completed successfully

### 4.3 Bootstrap Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_posthog_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

Coverage intent:

- env rendering includes the non-prod proxy/trusted-proxy defaults
- bundle rendering writes the expected deployment, proxy, backup, and credentials artifacts

### 4.4 Bootstrap Helper Smoke Render

Command shape:

```bash
python infra/scripts/posthog_bootstrap.py render-bundle \
  --domain posthog-nonprod.example.com \
  --admin-cidr 198.51.100.10/32 \
  --tls-email ops@example.com \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `.env`
  - `docker-compose.override.yml`
  - `nginx/posthog-http.conf`
  - `nginx/posthog-https.conf`
  - `compose/start`
  - `install-node.sh`

### 4.5 Stack Lockfile

Observed artifact:

- `infra/terraform/live/staging/posthog/.terraform.lock.hcl`

Interpretation:

- the new stack is pinned and reproducible under the current `OpenTofu` toolchain

### 4.6 Workspace Readiness Check For Live PostHog Evidence

Observed in the current workspace on 2026-04-22:

- no `backend.hcl` is present under `infra/terraform/live/staging/posthog`
- no real `TF_VAR_hcloud_token` or remote-backend credentials are present for a live stack apply
- no real DNS or ACME inputs are present for live TLS issuance
- no live host outputs exist from a real `tofu apply`

Meaning:

- live `tofu init/plan/apply` cannot be executed honestly from this workspace yet
- live bundle installation evidence cannot be attached yet
- live `NGINX`, TLS, login, capture, and backup evidence cannot be attached yet
- the blocker is missing operator-provided backend config, cloud credentials, and real domain inputs, not missing repo automation

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. `staging/posthog` is a separate stack from:
   - `staging/foundation`
   - `staging/openbao`
   - `staging/nats`
   - `staging/edge`
   - `staging/dns`
   - `staging/control-plane`
2. the new stack reads only `staging/foundation` remote state for SSH key names
3. canonical ids remain:
   - `environment = nonprod`
   - `posthog_instance_id = posthog-nonprod`
4. no legacy control-plane state was merged or extended
5. no live infrastructure apply was executed as part of this repo/validation slice

Explicitly not changed:

- legacy `staging` implementation path naming on disk
- current `foundation`, `openbao`, `nats`, `edge`, `dns`, and `control-plane` state boundaries
- actual application SDK or server-side capture rollout
- live event taxonomy enforcement inside running product flows

---

## 6. Residuals Before Packet Closure

Open residuals:

1. `remote-backend apply evidence` for the first real non-prod `PostHog` stack apply is still pending.
2. `bundle installation evidence` for the live host is still pending.
3. `live domain and DNS evidence` is still pending.
4. `NGINX and TLS evidence` is still pending.
5. `login or protected UI evidence` is still pending.
6. `capture or identify smoke evidence` is still pending.
7. `baseline local backup execution evidence` is still pending.

These residuals block a full `P1.4 complete` claim, but they do **not** invalidate the already-completed repository and validation slice above.

---

## 7. Recommended Next Live Commands

When operator-provided `backend.hcl`, cloud credentials, and domain inputs exist, the first honest live sequence should be:

```bash
tofu -chdir=infra/terraform/live/staging/posthog init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/posthog plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/posthog apply -var-file=terraform.tfvars
```

Then from the repository workspace:

```bash
python infra/scripts/posthog_bootstrap.py render-bundle \
  --domain <real-domain> \
  --admin-cidr <approved-admin-cidr> \
  --tls-email <ops-email> \
  --output-dir infra/artifacts/posthog-bootstrap/posthog-nonprod
```

Then on the provisioned host:

```bash
sudo /path/to/install-node.sh
sudo systemctl status --no-pager nginx
sudo /usr/local/sbin/posthog-local-backup.sh
```

Evidence for each step should be archived under:

```text
docs/evidence/platform-foundation/2026-04-22/p1-4-posthog-nonprod-foundation/
```
