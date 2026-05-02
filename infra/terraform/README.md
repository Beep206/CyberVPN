# OpenTofu Infrastructure

This directory contains the staging-first OpenTofu scaffold for CyberVPN.

The path name remains `infra/terraform/` as a legacy implementation alias during migration, but the canonical CLI for this directory is `tofu`.

## Layout

- `modules/` holds reusable infrastructure building blocks.
- `live/staging/*` holds the first runnable stacks for staging.
- `live/production/*` now mirrors the staging layout for controlled production canaries.
- `live/*/control-plane` is reserved for Phase 7 host provisioning and control-plane labels.

## Current Scope

Phase 0/1 covers:

- foundation resources for staging;
- non-prod OpenBao foundation resources for the legacy `staging/openbao` path;
- shared non-prod NATS JetStream foundation resources for the legacy `staging/nats` path;
- non-prod PostHog foundation resources for the legacy `staging/posthog` path;
- non-prod Talos management-cluster foundation resources for the legacy `staging/nonprod-mgmt` path;
- production Talos management-cluster foundation resources for the legacy `production/prod-mgmt` path;
- reusable edge node module;
- reusable control-plane node module;
- reusable Talos node module;
- separate DNS stack for Cloudflare records;
- S3 backend scaffolding with lockfile support.

## Staging Flow

1. Apply `live/staging/foundation`.
2. Apply `live/staging/openbao` for the canonical `nonprod` OpenBao foundation.
3. Apply `live/staging/nats` for the canonical shared `nonprod` JetStream foundation.
4. Apply `live/staging/posthog` for the canonical `nonprod` PostHog foundation.
5. Apply `live/staging/nonprod-mgmt` for the canonical `nonprod-mgmt` Talos management cluster.
6. Apply `live/staging/edge`.
7. Apply `live/staging/dns`.
8. Apply `live/staging/control-plane` when Phase 7 rollout starts.

The `edge` stack reads the `foundation` outputs through `terraform_remote_state`.
The `dns` stack reads the `edge` outputs through `terraform_remote_state`.
The `openbao` stack reads the `foundation` SSH key registry through `terraform_remote_state`.
The `nats` stack reads the `foundation` SSH key registry through `terraform_remote_state`.
The `posthog` stack reads the `foundation` SSH key registry through `terraform_remote_state`.
The `nonprod-mgmt` stack is intentionally separate and does not read legacy host bootstrap state from `foundation`.

## Production Flow

1. Apply `live/production/foundation`.
2. Apply `live/production/prod-mgmt` for the canonical `prod-mgmt` Talos management cluster.
3. Apply `live/production/edge` with canary nodes only.
4. Apply `live/production/dns` after the edge canary is healthy.
5. Apply `live/production/control-plane` only after the control-plane rollout plan is approved.

The `prod-mgmt` stack is intentionally separate and does not read legacy host bootstrap state from `foundation`.

## Usage

1. Copy `backend.hcl.example` to `backend.hcl` inside the stack you want to initialize.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export provider credentials:
   - `TF_VAR_hcloud_token`
   - `TF_VAR_cloudflare_api_token` for DNS stacks
   - `AWS_PROFILE` or `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` for the OpenBao KMS stack
4. Run from [`infra/Makefile`](/home/beep/projects/VPNBussiness/infra/Makefile) or directly with `tofu -chdir=...`.

## Conventions

- Split state by stack: `foundation`, `edge`, `dns`, and later `control-plane`.
- Keep provider tokens out of `terraform.tfvars`.
- Use `location`, not `datacenter`, for new Hetzner resources.
- Treat `tofu -target` as break-glass only.

## Naming

- environment firewall: `cybervpn-<env>-edge`
- OpenBao cluster id: `openbao-<env>` like `openbao-nonprod`
- NATS cluster id: `nats-<env>` like `nats-nonprod`
- PostHog instance id: `posthog-<env>` like `posthog-nonprod`
- management cluster id: `<env>-mgmt` like `nonprod-mgmt` or `prod-mgmt`
- edge node hostname: `<country>-<index>` like `fi-01`
- primary IPv4: `<hostname>-ipv4`
- staging DNS: `<hostname>.staging.<domain>`
- production DNS: `<hostname>.<domain>`
