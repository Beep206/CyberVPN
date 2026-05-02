# production/dns

Runnable production DNS stack for Cloudflare A records backed by the production edge state.

Before first use:

1. Apply `../edge` and confirm the canary nodes are healthy.
2. Copy `backend.hcl.example` to `backend.hcl`.
3. Copy `terraform.tfvars.example` to `terraform.tfvars`.
4. Export `TF_VAR_cloudflare_api_token`.

Keep production DNS changes narrow while the canary window is still open.

Typical operator path:

```bash
tofu -chdir=infra/terraform/live/production/dns init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/production/dns plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/production/dns apply -var-file=terraform.tfvars
```
