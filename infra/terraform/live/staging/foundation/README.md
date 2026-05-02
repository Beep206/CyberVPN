# staging/foundation

This stack owns shared staging resources:

- Hetzner SSH keys;
- default edge firewall for staging.

It should be applied before the staging `edge` stack.

Before first use:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Export `TF_VAR_hcloud_token`.

Typical operator path:

```bash
tofu -chdir=infra/terraform/live/staging/foundation init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/foundation plan
tofu -chdir=infra/terraform/live/staging/foundation apply
```
