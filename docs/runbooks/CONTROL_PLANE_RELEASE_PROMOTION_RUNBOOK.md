# Control Plane Release Promotion

This runbook covers the Phase 8 release-promotion and secrets-hardening flow for
the control-plane stack.

## Preconditions

1. A staging or production control-plane inventory already exists.
2. Private GHCR pulls are allowed and the host can receive registry credentials.
3. The target environment keeps manual approval enabled in GitHub Environments for
   production promotions.

## Build and publish images

Use the `Control Plane Images` workflow or an equivalent local pipeline to publish:

- `backend`
- `task-worker`
- `helix-adapter`

Each publish must yield a digest ref in the form:

```text
ghcr.io/<owner>/<repo>/<image>@sha256:<64-hex>
```

Do not promote mutable tags such as `latest`, `staging`, or branch tags.

## Update the release manifest

You can promote images locally:

```bash
cd /home/beep/projects/VPNBussiness/infra
make control-plane-release-staging \
  BACKEND_IMAGE=ghcr.io/<owner>/<repo>/backend@sha256:<digest> \
  WORKER_IMAGE=ghcr.io/<owner>/<repo>/task-worker@sha256:<digest> \
  HELIX_ADAPTER_IMAGE=ghcr.io/<owner>/<repo>/helix-adapter@sha256:<digest> \
  SOURCE_COMMIT=<git-sha>
```

Or use the `Control Plane Promote Release` workflow, which creates a promotion
branch with the updated `release.yml`.

Environment-specific manifest paths:

- `infra/ansible/inventories/staging/group_vars/control_plane_staging/release.yml`
- `infra/ansible/inventories/production/group_vars/control_plane_production/release.yml`

## Bootstrap vaulted secrets from a structured source file

Start from:

```text
infra/ansible/examples/control-plane-vault-source.yml.example
```

Render the target vault file:

```bash
cd /home/beep/projects/VPNBussiness/infra
make control-plane-vault-bootstrap-staging \
  SECRETS_SOURCE=/secure/path/control-plane-staging.yml
```

To encrypt immediately:

```bash
cd /home/beep/projects/VPNBussiness/infra
make control-plane-vault-bootstrap-staging \
  SECRETS_SOURCE=/secure/path/control-plane-staging.yml \
  ENCRYPT_VAULT=1 \
  VAULT_PASSWORD_FILE=/secure/path/.vault-pass.txt
```

If GHCR pulls are private, populate:

- `vault_control_plane_registry_username`
- `vault_control_plane_registry_password`

The control-plane rollout logs in to the configured registry before `docker compose`
pulls the release images.

## Roll out the target environment

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-rollout-staging
make ansible-control-plane-verify-staging
make ansible-control-plane-backup-staging
```

For production, keep the same flow but use the `*_production` targets and require
an approved promotion branch before merge and rollout.

## Evidence to collect

Capture and attach:

- commit SHA that produced the digests
- CI run URL or build evidence URL
- final `release.yml`
- rollout verification output
- backup evidence path under `/var/backups/cybervpn/`
