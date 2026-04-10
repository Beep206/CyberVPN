# staging/control-plane

This stack provisions staging control-plane hosts after `staging/foundation`.

Typical flow:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export `TF_VAR_hcloud_token`.
4. Initialize and apply:

```bash
terraform -chdir=infra/terraform/live/staging/control-plane init -backend-config=backend.hcl
terraform -chdir=infra/terraform/live/staging/control-plane plan -var-file=terraform.tfvars
terraform -chdir=infra/terraform/live/staging/control-plane apply -var-file=terraform.tfvars
```

`control_plane_nodes` is intentionally thin: the stack creates host(s), SSH
access, and labels. Service rollout stays in Ansible Phase 7 playbooks.
