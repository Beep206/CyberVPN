# production/foundation

Runnable production foundation stack for:

- shared production edge firewall;
- production Hetzner SSH key registration;
- shared labels used by later production stacks.

Before first use:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Replace all example CIDRs and SSH keys with real production values.
4. Export `TF_VAR_hcloud_token`.

This stack should be applied before `production/edge`.
