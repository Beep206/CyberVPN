# staging/nonprod-mgmt

This stack provisions the legacy `staging` implementation path for the canonical
`nonprod-mgmt` Talos management cluster.

It creates:

- one reserved Hetzner primary IPv4 for the stable Kubernetes API endpoint;
- one control-plane node and at least two worker nodes booting from a Talos image or snapshot;
- a Hetzner firewall that exposes:
  - Talos API (`50000/tcp`) from approved admin CIDRs only;
  - Kubernetes API (`6443/tcp`) from approved admin CIDRs and cluster nodes;
  - broad node-to-node TCP/UDP only between the cluster nodes, to keep first bootstrap and
    default Flannel networking functional on public-node topology;
- first-pass Talos bootstrap through the `siderolabs/talos` provider:
  - machine secrets
  - machine configuration apply
  - first control-plane bootstrap
  - kubeconfig retrieval

Typical flow:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Set `image` for all nodes to the validated Talos Hetzner image or snapshot ID for your project.
4. Export `TF_VAR_hcloud_token`.
5. Initialize and apply:

```bash
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt apply -var-file=terraform.tfvars
```

After the cluster exists, save the sensitive outputs out of band:

```bash
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt output -raw talosconfig > /secure/path/nonprod-mgmt.talosconfig
tofu -chdir=infra/terraform/live/staging/nonprod-mgmt output -raw kubeconfig_raw > /secure/path/nonprod-mgmt.kubeconfig
```

Then render the canonical Cluster API install bundle:

```bash
python infra/scripts/nonprod_mgmt_bootstrap.py render-bundle \
  --kubeconfig-path /secure/path/nonprod-mgmt.kubeconfig \
  --output-dir infra/artifacts/nonprod-mgmt-bootstrap
```

Run the rendered bundle on an operator workstation with `clusterctl` and `kubectl`:

1. `bash install-capi-core.sh`
2. Set `CAPH_COMPONENTS_URL` to a validated `infrastructure-components.yaml` compatible with
   `CAPI v1.13.x`
3. `bash install-caph.sh`

Important compatibility note:

- `clusterctl` defaults the Hetzner provider to the latest stable release asset, but as of
  2026-04-22 the stable `CAPH v1.0.x` line is documented upstream as incompatible with
  `CAPI v1.11+`.
- The rendered bundle therefore installs core CAPI plus Talos providers first, and keeps the
  Hetzner provider as an explicit operator-pinned step until a validated `v1.1.x` or newer
  compatible asset is chosen for this program.

`staging/nonprod-mgmt` is an implementation path only. The canonical environment id and
management-cluster id remain `nonprod` and `nonprod-mgmt`.
