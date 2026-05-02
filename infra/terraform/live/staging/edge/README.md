# staging/edge

This stack creates staging edge nodes.

It expects the `staging/foundation` stack state to be readable through `terraform_remote_state`.

Before first use:

1. Apply `../foundation`.
2. Copy `backend.hcl.example` to `backend.hcl`.
3. Copy `terraform.tfvars.example` to `terraform.tfvars`.
4. Export `TF_VAR_hcloud_token`.

Typical operator path:

```bash
tofu -chdir=infra/terraform/live/staging/edge init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/edge plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/edge apply -var-file=terraform.tfvars
```
