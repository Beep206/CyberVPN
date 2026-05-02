# staging/dns

This stack manages staging DNS records in Cloudflare.

Keep it intentionally thin:

- one zone per stack;
- one record map in variables;
- no large module abstraction for basic DNS records.

For the Cloudflare v5 provider, prefer full record names (FQDN) or `@` for the zone apex.
This stack reads the staging edge node IPs from the `staging/edge` remote state.

Before first use:

1. Apply `../edge`.
2. Copy `backend.hcl.example` to `backend.hcl`.
3. Copy `terraform.tfvars.example` to `terraform.tfvars`.
4. Export `TF_VAR_cloudflare_api_token`.

Typical operator path:

```bash
tofu -chdir=infra/terraform/live/staging/dns init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/dns plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/dns apply -var-file=terraform.tfvars
```
