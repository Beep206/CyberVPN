# Production Edge Canary Runbook

This runbook covers Phase 6: one production Remnawave edge canary and one production Helix edge canary.

## Preconditions

1. Production inventory must be generated from the production Terraform `edge` stack.
2. `inventories/production/group_vars/*` must be filled with real production values and vaulted secrets.
3. GitHub environment approval must remain manual for production rollout.
4. Choose exactly one host for the Remnawave canary and one host for the Helix canary.

## Inventory generation

Before inventory generation, initialize and apply the production Terraform stacks in order:

```bash
cd /home/beep/projects/VPNBussiness/infra
make terraform-init-production-foundation
make terraform-plan-production-foundation
make terraform-init-production-edge
make terraform-plan-production-edge
```

The production edge stack must already have a real remote state before inventory generation can work.

```bash
cd /home/beep/projects/VPNBussiness/infra
make inventory-production
```

This produces:

- `ansible/inventories/production/generated.hosts.json`
- `artifacts/prometheus/production/alloy-edge.json`

Do not drop the generated Prometheus target file into the local dev stack by accident. Treat it as an operator artifact and apply it only on the monitoring host that should scrape production edge nodes.

## Remnawave production canary

```bash
cd /home/beep/projects/VPNBussiness/infra
PROD_REMNAWAVE_CANARY_HOST=<inventory-hostname> make ansible-phase6-remnawave-canary-production
```

If the rollout regresses:

```bash
cd /home/beep/projects/VPNBussiness/infra
cd ansible
ansible-playbook -i inventories/production playbooks/rollback-remnawave.yml \
  -e remnawave_edge_target_group=remnawave_edge_production \
  --limit "<inventory-hostname>"
```

## Helix production canary

```bash
cd /home/beep/projects/VPNBussiness/infra
PROD_HELIX_CANARY_HOST=<inventory-hostname> make ansible-phase6-helix-canary-production
```

If the rollout regresses:

```bash
cd /home/beep/projects/VPNBussiness/infra
cd ansible
ansible-playbook -i inventories/production playbooks/rollback-helix.yml \
  -e helix_edge_target_group=helix_edge_production \
  --limit "<inventory-hostname>"
```

## Observation window

1. Observe the canary for 24 hours before widening blast radius.
2. Confirm workload health and Alloy telemetry for the same host.
3. Keep the generated inventory and Prometheus target artifacts with the rollout notes.
4. Only after the 24-hour window should additional hosts be considered.
