# staging/nats

This stack provisions the legacy `staging` implementation path for the canonical
shared `nonprod` NATS JetStream foundation.

It creates:

- three dedicated Hetzner VMs for the canonical `nats-nonprod` cluster;
- local-SSD JetStream storage paths on each node;
- a firewall that exposes:
  - SSH from administrative CIDRs;
  - the NATS client port from approved client CIDRs;
  - the cluster route port only between NATS node IPs;
  - the Prometheus NATS exporter port from approved metrics CIDRs;
- cloud-init bootstrap that installs pinned `nats-server` and `prometheus-nats-exporter`,
  writes systemd units, and leaves both services gated on bootstrap bundle files.

Typical flow:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export `TF_VAR_hcloud_token`.
4. Initialize and apply:

```bash
tofu -chdir=infra/terraform/live/staging/nats init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/nats plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/nats apply -var-file=terraform.tfvars
```

After the nodes exist, render the canonical bootstrap bundle:

```bash
tofu -chdir=infra/terraform/live/staging/nats output -json nats_nodes > /tmp/nats-nonprod-nodes.json

python infra/scripts/nats_bootstrap.py render-bundle \
  --cluster-name nats-nonprod \
  --nodes-file /tmp/nats-nonprod-nodes.json \
  --accounts-file infra/nats/examples/accounts.json.example \
  --output-dir infra/artifacts/nats-bootstrap/nats-nonprod
```

For each node, copy the rendered node directory to the host and run the generated
`install-node.sh` as root. That script installs:

- `/etc/nats/nats-server.conf`
- `/etc/nats/exporter.env`
- `/etc/nats/tls/ca.crt`
- `/etc/nats/tls/server.crt`
- `/etc/nats/tls/server.key`

and then restarts:

- `nats.service`
- `nats-exporter.service`

The rendered bundle also includes:

- `prometheus/nats-nonprod-targets.json`

Copy that file into the central Prometheus `file_sd` directory as `nats-*.json`. The
local Docker Compose Prometheus baseline now scrapes `nats-*.json` through the
dedicated `nats-exporter` job.

Useful source-controlled inputs for the bootstrap helper live under:

- `infra/nats/examples/accounts.json.example`
- `infra/scripts/nats_bootstrap.py`

Treat the rendered output directory as sensitive:

- it contains generated user passwords in `credentials.json`;
- it contains the local CA private key under `ca/ca.key`;
- it must not be committed to git.

`staging/nats` is an implementation path only. The canonical environment id and
cluster id remain `nonprod` and `nats-nonprod`.
