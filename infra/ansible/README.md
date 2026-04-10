# Ansible Infrastructure

This directory contains the staging-first Ansible rollout scaffold for CyberVPN.

## Current Scope

Phase 0/1 and Phase 2 provide:

- inventory layout for staging and production;
- baseline `base` and `docker` roles;
- a bootstrap playbook for edge hosts.

Phase 3 adds:

- `remnawave_edge` role with pinned `remnawave/node` deploys;
- deterministic release directories under `/opt/cybervpn/remnanode/releases`;
- `current` and `previous` symlinks for rollback;
- rollout, verify, and rollback playbooks for Remnawave edge nodes.

Phase 4 adds:

- `helix_edge` role for the `helix-node` daemon;
- persistent host state under `/var/lib/helix-node`;
- staged canary rollout with a pause after the first node;
- rollout, verify, and rollback playbooks for Helix edge nodes.

Phase 5 adds:

- `alloy_agent` role for edge logs and rollout telemetry;
- Alloy canary rollout, verify, and rollback playbooks;
- a fixture-backed inventory snapshot flow for CI artifacts;
- a generated Prometheus file_sd target snapshot for `alloy-edge` scraping;
- edge observability dashboard and Alloy alert wiring.

## Usage

1. Install collections:

```bash
cd infra/ansible
ansible-galaxy collection install -r requirements.yml
```

2. Populate inventory:

- for a quick manual check, edit `ansible/inventories/staging/hosts.yml`;
- for the normal staging flow, generate a snapshot from Terraform outputs:

```bash
cd infra
make inventory-staging
```

Equivalent direct command:

```bash
cd infra/ansible
python scripts/generate_inventory.py \
  --terraform-dir ../terraform/live/staging/edge \
  --output inventories/staging/generated.hosts.json \
  --environment staging
```

3. Run a syntax check:

```bash
cd infra/ansible
ansible-playbook -i inventories/staging playbooks/site.yml --syntax-check
```

4. Bootstrap and verify staging hosts:

```bash
cd infra
make ansible-phase2-staging
```

This runs:

- inventory snapshot generation from Terraform outputs;
- edge bootstrap (`base` + `docker`);
- post-bootstrap verification checks.

## Phase 3 usage

1. Prepare Remnawave node secrets:

```bash
cd infra/ansible
cp inventories/staging/group_vars/remnawave_edge_staging/vault.yml.example \
   inventories/staging/group_vars/remnawave_edge_staging/vault.yml
ansible-vault encrypt inventories/staging/group_vars/remnawave_edge_staging/vault.yml
```

`vault_remnawave_edge_secret_key` must match the `SECRET_KEY` you would otherwise copy from the Remnawave panel node payload.

2. Verify `remnawave_edge_node_port` in:

- `ansible/inventories/staging/group_vars/remnawave_edge_staging/main.yml`

It must match the node port configured in the Remnawave panel.
Restrict this port in cloud firewall rules to the panel IP or CIDR only.

3. Run the rollout:

```bash
cd infra
make ansible-phase3-staging
```

Equivalent direct commands:

```bash
cd infra
make inventory-staging

cd ansible
ansible-playbook -i inventories/staging playbooks/remnawave-rollout.yml
ansible-playbook -i inventories/staging playbooks/remnawave-verify.yml
```

4. Roll back to the previously linked release if needed:

```bash
cd infra
make ansible-remnawave-rollback-staging
```

Optional targeted rollback:

```bash
cd infra/ansible
ansible-playbook -i inventories/staging playbooks/rollback-remnawave.yml \
  -e remnawave_edge_rollback_release_name=remnanode-<release-id>
```

## Phase 4 usage

1. Prepare Helix secrets:

```bash
cd infra/ansible
cp inventories/staging/group_vars/helix_edge_staging/vault.yml.example \
   inventories/staging/group_vars/helix_edge_staging/vault.yml
ansible-vault encrypt inventories/staging/group_vars/helix_edge_staging/vault.yml
```

2. Fill the required Helix rollout vars in:

- `inventories/staging/group_vars/helix_edge_staging/main.yml`

At minimum set:

- `helix_edge_image`
- `helix_edge_adapter_url`
- `helix_edge_node_id`
- `helix_edge_transport_ports`

`helix_edge_adapter_token` comes from the vaulted `vault_helix_edge_adapter_token`.

3. Match the Ansible vars to adapter-side node registration:

- `helix_edge_node_id` must match the adapter node record;
- `helix_edge_transport_ports` must match the transport port(s) assigned for that node;
- set `helix_edge_allow_private_targets: true` only for lab/private-target scenarios.

4. Run the rollout:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase4-staging
```

Equivalent direct commands:

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-staging

cd ansible
ansible-playbook -i inventories/staging playbooks/helix-rollout.yml
ansible-playbook -i inventories/staging playbooks/helix-verify.yml
```

5. Roll back if needed:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-helix-rollback-staging
```

Optional targeted rollback:

```bash
cd /home/beep/projects/VPNBussiness/infra/ansible
ansible-playbook -i inventories/staging playbooks/rollback-helix.yml \
  -e helix_edge_rollback_release_name=helix-node-<release-id>
```

The Helix control endpoint is bound to loopback by default through
`helix_edge_control_publish_host=127.0.0.1`. Override it only if you intentionally need
remote access to `/healthz`, `/readyz`, or `/metrics`.

## Phase 5 usage

1. Prepare Alloy edge vars in:

- `inventories/staging/group_vars/edge_staging/alloy.yml`

At minimum set:

- `alloy_agent_loki_url`

If the Loki endpoint requires authentication, use exactly one of:

- vaulted `vault_alloy_agent_loki_basic_auth_username` + `vault_alloy_agent_loki_basic_auth_password`
- vaulted `vault_alloy_agent_loki_bearer_token`

2. Run the rollout:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase5-staging
```

Equivalent direct commands:

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-staging

cd ansible
ansible-playbook -i inventories/staging playbooks/alloy-rollout.yml
ansible-playbook -i inventories/staging playbooks/alloy-verify.yml
```

3. Roll back if needed:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-alloy-rollback-staging
```

4. For CI-only inventory artifacts without a real Terraform state:

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-fixture-staging
```

This writes both:

- `artifacts/iac-ci/generated.hosts.json`
- `artifacts/iac-ci/alloy-edge.json`

## Release layout

Each rollout renders a deterministic release directory based on the effective Compose and env payload:

- `/opt/cybervpn/remnanode/releases/remnanode-<fingerprint>/`
- `/opt/cybervpn/remnanode/current`
- `/opt/cybervpn/remnanode/previous`

If a rollout fails after switching `current`, the role attempts an automatic rollback to the last known good release before returning failure.

## Vault bootstrap

Environment-specific vaulted placeholders live under:

- `ansible/inventories/staging/group_vars/edge_staging/vault.yml.example`
- `ansible/inventories/staging/group_vars/remnawave_edge_staging/vault.yml.example`
- `ansible/inventories/staging/group_vars/helix_edge_staging/vault.yml.example`
- `ansible/inventories/staging/group_vars/control_plane_staging/vault.yml.example`
- `ansible/inventories/production/group_vars/edge_production/vault.yml.example`
- `ansible/inventories/production/group_vars/remnawave_edge_production/vault.yml.example`
- `ansible/inventories/production/group_vars/helix_edge_production/vault.yml.example`
- `ansible/inventories/production/group_vars/control_plane_production/vault.yml.example`

Recommended bootstrap flow:

```bash
cd infra/ansible
cp inventories/staging/group_vars/edge_staging/vault.yml.example \
   inventories/staging/group_vars/edge_staging/vault.yml
ansible-vault encrypt inventories/staging/group_vars/edge_staging/vault.yml
```

## Conventions

- do not store vault passwords in git;
- keep environment-specific secrets outside repo;
- generated inventory snapshots are derived artifacts and should not be committed;
- start with staging inventory only;
- keep `remnawave_edge_image` pinned and upgrade intentionally;
- match `remnawave_edge_node_port` and `vault_remnawave_edge_secret_key` with the panel-side node definition;
- keep `helix_edge_image` pinned and sourced from a published image, not an ad-hoc host build;
- match `helix_edge_node_id`, adapter URL/token, and published transport ports with the adapter-side registry;
- keep `/var/lib/helix-node` persistent across releases to preserve last-known-good rollback state;
- keep generated inventory snapshots as derived artifacts and do not commit them;
- keep generated Prometheus target snapshots as derived artifacts and do not commit them;
- keep `alloy_agent_http_port` aligned with the Terraform edge metrics port and open it only to monitoring CIDRs;
- keep Alloy rollout manual and operator-approved; do not auto-apply it from merge-triggered workflows;
- keep control-plane internal images pinned in environment `release.yml` files by digest, not by mutable tags or ad-hoc host builds;
- keep control-plane API and metrics ports loopback-bound unless a reviewed ingress layer is introduced explicitly;
- keep `backup_restore` dumps under `/var/backups/cybervpn/postgres` and collect config snapshots before restore drills;
- use the post-deploy checklist in `docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md`.

## Phase 6 usage

Production canary rollout stays explicit and host-limited.

1. Generate production inventory:

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-production
```

This requires a real initialized production Terraform backend and an existing
`production/edge` state. It will not work against examples alone.

2. Run the Remnawave production canary on one host:

```bash
cd /home/beep/projects/VPNBussiness/infra
PROD_REMNAWAVE_CANARY_HOST=<inventory-hostname> make ansible-phase6-remnawave-canary-production
```

3. Run the Helix production canary on one host:

```bash
cd /home/beep/projects/VPNBussiness/infra
PROD_HELIX_CANARY_HOST=<inventory-hostname> make ansible-phase6-helix-canary-production
```

Use `docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md` for the manual observation and rollback flow.

## Phase 7 usage

Phase 7 stays repo-level until you have a real control-plane inventory and real vaulted secrets.

1. Provision control-plane host(s):

```bash
cd /home/beep/projects/VPNBussiness/infra
terraform -chdir=terraform/live/staging/control-plane init -backend-config=backend.hcl
terraform -chdir=terraform/live/staging/control-plane plan -var-file=terraform.tfvars
```

2. Populate control-plane vars and vault:

- `ansible/inventories/staging/group_vars/control_plane_staging/main.yml`
- `ansible/inventories/staging/group_vars/control_plane_staging/release.yml`
- `ansible/inventories/staging/group_vars/control_plane_staging/vault.yml`

3. Roll out the control-plane stack:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-rollout-staging
make ansible-control-plane-verify-staging
```

4. Capture backup evidence and optional restore drill helper:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-backup-staging
make ansible-control-plane-restore-drill-staging
```

Production uses the same playbooks with the `*_production` targets once real
inventory and vault files exist.

## Phase 8 usage

Phase 8 turns control-plane rollout into a manifest-driven promotion flow.

1. Publish digest-pinned images for `backend`, `task-worker`, and `helix-adapter`.

2. Update the release manifest:

```bash
cd /home/beep/projects/VPNBussiness/infra
make control-plane-release-staging \
  BACKEND_IMAGE=ghcr.io/<owner>/<repo>/backend@sha256:<digest> \
  WORKER_IMAGE=ghcr.io/<owner>/<repo>/task-worker@sha256:<digest> \
  HELIX_ADAPTER_IMAGE=ghcr.io/<owner>/<repo>/helix-adapter@sha256:<digest> \
  SOURCE_COMMIT=<git-sha>
```

3. Bootstrap the vault from a structured source file:

```bash
cd /home/beep/projects/VPNBussiness/infra
make control-plane-vault-bootstrap-staging \
  SECRETS_SOURCE=/secure/path/control-plane-staging.yml
```

4. Keep registry credentials vaulted if GHCR pulls are private:

- `vault_control_plane_registry_username`
- `vault_control_plane_registry_password`

5. Roll out and verify as usual:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-rollout-staging
make ansible-control-plane-verify-staging
make ansible-control-plane-backup-staging
```

See `docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md` for the full operator procedure.
