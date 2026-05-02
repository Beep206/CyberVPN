# staging/posthog

This stack provisions the legacy `staging` implementation path for the canonical
`nonprod` PostHog foundation.

It creates:

- one dedicated Hetzner VM for the canonical `posthog-nonprod` instance;
- a firewall that exposes:
  - SSH from administrative CIDRs;
  - HTTP and HTTPS from approved ingress CIDRs;
- cloud-init bootstrap that installs Docker, Docker Compose, NGINX, Certbot, and
  a host-local baseline backup timer.

Typical flow:

1. Copy `backend.hcl.example` to `backend.hcl`.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export `TF_VAR_hcloud_token`.
4. Initialize and apply:

```bash
tofu -chdir=infra/terraform/live/staging/posthog init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/posthog plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/posthog apply -var-file=terraform.tfvars
```

After the node exists, render the canonical bootstrap bundle:

```bash
python infra/scripts/posthog_bootstrap.py render-bundle \
  --domain posthog.staging.example.com \
  --admin-cidr 203.0.113.10/32 \
  --tls-email ops@example.com \
  --output-dir infra/artifacts/posthog-bootstrap/posthog-nonprod
```

Copy the rendered bundle to the host and run `install-node.sh` as root. That script:

- clones the official `PostHog` repository;
- installs the self-hosted hobby compose files plus a local override;
- writes host-level `NGINX` reverse-proxy config;
- brings the Docker stack up;
- optionally requests TLS certificates with `certbot`;
- installs the baseline local-backup script.

The rendered output directory is sensitive and must not be committed to git because
it contains:

- generated PostHog secrets;
- generated basic-auth credentials for the protected UI path;
- deployment environment files.

`staging/posthog` is an implementation path only. The canonical environment id and
instance id remain `nonprod` and `posthog-nonprod`.
