# production/control-plane

This stack provisions production control-plane hosts after `production/foundation`.

Typical flow:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export `TF_VAR_hcloud_token`.
4. Initialize and plan:

```bash
terraform -chdir=infra/terraform/live/production/control-plane init -backend-config=backend.hcl
terraform -chdir=infra/terraform/live/production/control-plane plan -var-file=terraform.tfvars
```

The stack keeps its scope narrow:

- host provisioning;
- control-plane SSH firewall;
- labels and outputs for Ansible.

Application rollout, backups, and DR drills stay in the Phase 7 Ansible layer.
