# Terraform Infrastructure

This directory contains the staging-first Terraform scaffold for CyberVPN.

## Layout

- `modules/` holds reusable infrastructure building blocks.
- `live/staging/*` holds the first runnable stacks for staging.
- `live/production/*` now mirrors the staging layout for controlled production canaries.
- `live/*/control-plane` is reserved for Phase 7 host provisioning and control-plane labels.

## Current Scope

Phase 0/1 covers:

- foundation resources for staging;
- reusable edge node module;
- reusable control-plane node module;
- separate DNS stack for Cloudflare records;
- S3 backend scaffolding with lockfile support.

## Staging Flow

1. Apply `live/staging/foundation`.
2. Apply `live/staging/edge`.
3. Apply `live/staging/dns`.
4. Apply `live/staging/control-plane` when Phase 7 rollout starts.

The `edge` stack reads the `foundation` outputs through `terraform_remote_state`.
The `dns` stack reads the `edge` outputs through `terraform_remote_state`.

## Production Flow

1. Apply `live/production/foundation`.
2. Apply `live/production/edge` with canary nodes only.
3. Apply `live/production/dns` after the edge canary is healthy.
4. Apply `live/production/control-plane` only after the control-plane rollout plan is approved.

## Usage

1. Copy `backend.hcl.example` to `backend.hcl` inside the stack you want to initialize.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Export provider credentials:
   - `TF_VAR_hcloud_token`
   - `TF_VAR_cloudflare_api_token`
4. Run from [`infra/Makefile`](/home/beep/projects/VPNBussiness/infra/Makefile) or directly with `terraform -chdir=...`.

## Conventions

- Split state by stack: `foundation`, `edge`, `dns`, and later `control-plane`.
- Keep provider tokens out of `terraform.tfvars`.
- Use `location`, not `datacenter`, for new Hetzner resources.
- Treat `terraform -target` as break-glass only.

## Naming

- environment firewall: `cybervpn-<env>-edge`
- edge node hostname: `<country>-<index>` like `fi-01`
- primary IPv4: `<hostname>-ipv4`
- staging DNS: `<hostname>.staging.<domain>`
- production DNS: `<hostname>.<domain>`
