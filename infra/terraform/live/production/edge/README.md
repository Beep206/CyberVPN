# production/edge

Runnable production edge stack for a controlled canary rollout.

Recommended first apply:

- one Remnawave production canary node;
- one Helix production canary node.

Before first use:

1. Apply `../foundation`.
2. Copy `backend.hcl.example` to `backend.hcl`.
3. Copy `terraform.tfvars.example` to `terraform.tfvars`.
4. Keep `edge_nodes` limited to the intended canary hosts until the 24-hour observation window is complete.
5. Export `TF_VAR_hcloud_token`.
