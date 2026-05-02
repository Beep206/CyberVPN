# CyberVPN Platform Foundation OpenBao And PKI Registry

**Date:** 2026-04-21  
**Status:** Frozen baseline for `T0.3`

This document freezes the canonical naming, trust-boundary model, auth mount conventions, policy naming, PKI mount layout, and bootstrap exceptions for the CyberVPN secrets and PKI plane.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](../plans/2026-04-21-platform-foundation-naming-and-boundary-registry.md)

This registry exists so later implementation phases do not invent conflicting names for:

- OpenBao clusters;
- KMS trust anchors;
- namespaces;
- auth mounts;
- policies and roles;
- PKI engines and trust domains;
- bootstrap exception paths.

## 1. Canonical Platform Decisions Frozen Here

The following decisions are already fixed and are not reopened by this registry:

1. `OpenBao` is the canonical secrets-plane.
2. `prod` and `nonprod` use separate OpenBao clusters.
3. OpenBao runs outside Kubernetes on dedicated VMs.
4. `prod` uses `3-node` integrated Raft.
5. `nonprod` starts with `1-node` integrated Raft.
6. Auto-unseal uses `AWS KMS`.
7. Kubernetes authenticates to OpenBao using `JWT auth` by default.
8. Humans authenticate using `OIDC`, not local usernames/passwords.
9. `AppRole` is reserved for narrow bootstrap and migration exceptions only.
10. Internal PKI uses an offline root and environment-specific intermediates in OpenBao.

## 2. Canonical Cluster And Trust-Anchor Identifiers

Frozen cluster identifiers:

| Environment | Canonical OpenBao cluster id |
|---|---|
| `prod` | `openbao-prod` |
| `nonprod` | `openbao-nonprod` |

Frozen trust-anchor naming:

| Environment | AWS KMS key alias | Purpose |
|---|---|---|
| `prod` | `alias/openbao/prod/seal` | auto-unseal for `openbao-prod` |
| `nonprod` | `alias/openbao/nonprod/seal` | auto-unseal for `openbao-nonprod` |

Rules:

1. `prod` and `nonprod` must never share the same KMS key.
2. Separate AWS accounts for `prod` and `nonprod` are preferred; separate keys are mandatory.
3. OpenBao cluster names and KMS aliases are part of the trust model and must not drift between docs, Terraform/OpenTofu, and runbooks.

## 3. Namespace Model

OpenBao namespace notation in this document uses:

```text
<namespace>::<mount-or-path>
```

Examples:

- `root::auth/oidc-operators`
- `platform::auth/jwt-k8s-prod-hetzner-fsn1-apps`
- `platform::kv-apps/data/control-plane/backend`

Frozen namespace model:

| Namespace | Purpose | Allowed contents |
|---|---|---|
| `root` | operator, emergency, and platform-control functions only | audit config, root-level auth for operators, recovery flows, limited control mounts |
| `platform` | service-facing integrations and PKI engines | JWT auth mounts, cert auth, AppRole bootstrap exceptions, KV mounts, PKI mounts |

Rules:

1. `root` is not a general application namespace.
2. Day-to-day workload integration lives in `platform`, not in `root`.
3. Per-app namespaces are prohibited in the baseline.
4. Environment separation is achieved by separate OpenBao clusters, not by encoding `prod` and `nonprod` into every path.

## 4. Auth Mount Naming

### 4.1 Human Operator Auth

Frozen root-level mount:

- `root::auth/oidc-operators`

Purpose:

- human operator access;
- audited administrative workflows;
- no local password users.

### 4.2 Kubernetes Auth

Frozen naming pattern:

- `platform::auth/jwt-k8s-<cluster-id>`

Examples:

- `platform::auth/jwt-k8s-prod-hetzner-fsn1-apps`
- `platform::auth/jwt-k8s-nonprod-hetzner-fsn1-observability`

Rules:

1. Every Kubernetes cluster gets its own JWT auth mount.
2. Cluster id must match the canonical cluster naming registry from `T0.1`.
3. JWT auth mounts are cluster-scoped, not shared across multiple clusters.

### 4.3 Fleet Certificate Auth

Frozen reserved mount:

- `platform::auth/cert-fleet`

Purpose:

- steady-state certificate-based identity for external fleet nodes where practical.

### 4.4 Bootstrap AppRole Auth

Frozen reserved mount:

- `platform::auth/approle-bootstrap`

Purpose:

- narrow bootstrap exceptions only;
- never steady-state service auth.

## 5. Auth Role Naming

Frozen role naming patterns:

| Auth method | Role naming pattern |
|---|---|
| `JWT` | `k8s-<cluster-id>-<namespace>-<service-account>` |
| `OIDC` | `human-operators-<scope>` |
| `cert` | `fleet-<role>` |
| `AppRole` | `bootstrap-<system>-<purpose>` |

Examples:

- `k8s-prod-hetzner-fsn1-apps-backend-backend`
- `k8s-nonprod-hetzner-fsn1-observability-alloy-alloy`
- `human-operators-admin`
- `human-operators-readonly`
- `fleet-node-enrolled`
- `bootstrap-fleet-node-enrollment`
- `bootstrap-legacy-control-plane-migration`

Rules:

1. Role names must be deterministic from the owning subject.
2. `prod` and `nonprod` may appear inside cluster ids, but are not added separately to role names.
3. No wildcard role names like `default`, `app`, `node`, or `admin`.

## 6. Policy Naming

Frozen policy naming patterns:

| Policy class | Naming pattern |
|---|---|
| human operator | `root-human-operators-<scope>` |
| Kubernetes workload | `platform-k8s-<cluster-id>-<namespace>-<service-account>` |
| cert-auth fleet workload | `platform-fleet-<role>` |
| bootstrap exception | `platform-bootstrap-<system>-<purpose>` |
| PKI issuer | `platform-pki-<domain>-<role>` |

Examples:

- `root-human-operators-admin`
- `root-human-operators-readonly`
- `platform-k8s-prod-hetzner-fsn1-apps-backend-backend`
- `platform-fleet-node-enrolled`
- `platform-bootstrap-fleet-node-enrollment`
- `platform-pki-k8s-cert-manager`

Rules:

1. Policy names must be generated from ownership, not handwritten ad hoc.
2. Human, Kubernetes, fleet, and bootstrap policies must remain visually distinguishable.
3. Policies are not allowed to encode provider secrets or customer data in their names.

## 7. Secret Engine Mount Naming And Path Conventions

Frozen service-facing mounts inside `platform`:

| Mount | Purpose |
|---|---|
| `platform::kv-apps` | application and service secrets |
| `platform::kv-shared` | shared platform integrations and cross-service secrets |
| `platform::pki-k8s` | Kubernetes/internal service TLS |
| `platform::pki-infra` | infrastructure, ops, and internal endpoint TLS |
| `platform::pki-fleet` | reserved for external fleet/node PKI when required |

Rules:

1. Mount names are stable and must not be renamed per environment.
2. `pki-fleet` is reserved even if not enabled on day 1.
3. Environment separation happens by cluster boundary, not by adding `prod` or `nonprod` into every mount name.

### 7.1 `kv-apps` Path Convention

Frozen path pattern:

```text
platform::kv-apps/data/<service-surface>/<secret-set>
```

Examples:

- `platform::kv-apps/data/control-plane/backend`
- `platform::kv-apps/data/control-plane/task-worker`
- `platform::kv-apps/data/control-plane/helix-adapter`
- `platform::kv-apps/data/edge/alloy`

### 7.2 `kv-shared` Path Convention

Frozen path pattern:

```text
platform::kv-shared/data/<domain>/<secret-set>
```

Examples:

- `platform::kv-shared/data/registry/ghcr`
- `platform::kv-shared/data/integration/remnawave`
- `platform::kv-shared/data/helix/shared-auth`

Rules:

1. Shared mounts are for truly shared secrets, not for dumping arbitrary app env.
2. `.env` file structure is not the future path design.
3. Sensitive bootstrap material should be wrapped and short-lived rather than stored as a static long-lived secret where possible.

## 8. PKI Naming And Trust Domains

### 8.1 Root And Intermediate Model

Frozen model:

1. One offline root CA exists outside OpenBao runtime.
2. `openbao-prod` holds `prod` intermediates only.
3. `openbao-nonprod` holds `nonprod` intermediates only.
4. `prod` and `nonprod` must never share an intermediate.
5. OpenBao is not the public browser-certificate authority; Cloudflare/public edge owns public browser TLS.

### 8.2 Intermediate Mount Names

Frozen PKI mount names:

- `platform::pki-k8s`
- `platform::pki-infra`
- `platform::pki-fleet` reserved

### 8.3 Trust-Domain Naming

Frozen trust-domain pattern:

| PKI domain | Trust-domain format |
|---|---|
| Kubernetes/internal services | `k8s.<env>.internal.cybervpn` |
| infrastructure/ops/internal endpoints | `infra.<env>.internal.cybervpn` |
| external fleet, if enabled | `fleet.<env>.internal.cybervpn` |

Examples:

- `k8s.prod.internal.cybervpn`
- `infra.prod.internal.cybervpn`
- `k8s.nonprod.internal.cybervpn`
- `fleet.nonprod.internal.cybervpn`

Rules:

1. Workloads must not receive certificates from the wrong environment trust domain.
2. `prod` trusts do not sign `nonprod` identities and vice versa.
3. Public DNS and public browser certificates are outside these internal PKI domains.

### 8.4 PKI Role Naming

Frozen role naming patterns:

| Mount | Role pattern |
|---|---|
| `pki-k8s` | `k8s-<cluster-id>-<issuer-or-workload>` |
| `pki-infra` | `infra-<service-or-hostclass>` |
| `pki-fleet` | `fleet-<node-class-or-role>` |

Examples:

- `k8s-prod-hetzner-fsn1-apps-cert-manager`
- `infra-openbao-server`
- `infra-nats-server`
- `fleet-vpn-standard`

## 9. Bootstrap Exception Matrix

`AppRole` is not a general auth method. It is reserved for the following allowlisted cases only.

### 9.1 Allowed AppRole Cases

| Case | Canonical role | Why allowed |
|---|---|---|
| external fleet node first bootstrap | `bootstrap-fleet-node-enrollment` | node has no steady-state cert identity yet |
| temporary legacy control-plane migration automation | `bootstrap-legacy-control-plane-migration` | bounded transition from current Ansible-vault/.env world |

Rules for allowed AppRole usage:

1. Secret delivery must use response wrapping.
2. Wrapped material must be short-lived.
3. Secret IDs should be single-use where practical.
4. AppRole credentials must be bound to an owned provisioning or migration workflow.
5. AppRole must not survive as the node or workload steady-state identity.

### 9.2 Prohibited AppRole Cases

`AppRole` is explicitly prohibited for:

- Kubernetes workloads;
- Flux, Flagger, cert-manager, trust-manager, or platform controllers that can use JWT auth;
- human operators;
- long-lived node runtime identity;
- analytics ingestion and product-facing services in steady state;
- generic service-to-service auth.

## 10. Response Wrapping Baseline

Response wrapping is mandatory for bootstrap secret delivery.

Frozen baseline:

- wrapped secret delivery for bootstrap exceptions only;
- default wrapping TTL target: `<= 15m`;
- shorter TTL is preferred when the workflow allows it;
- wrapping token distribution must be one-time and workflow-scoped;
- wrapped secret material must not be copied into static inventory or persistent `.env` files.

## 11. Current Legacy Secret Model And Migration Anchors

The repository currently still uses:

- `.env` files across applications and infrastructure;
- Ansible-vault-rendered `vault.yml` for the current control-plane rollout;
- the helper script [infra/ansible/scripts/bootstrap_control_plane_vault.py](/home/beep/projects/VPNBussiness/infra/ansible/scripts/bootstrap_control_plane_vault.py:1);
- the structured source example [infra/ansible/examples/control-plane-vault-source.yml.example](/home/beep/projects/VPNBussiness/infra/ansible/examples/control-plane-vault-source.yml.example:1).

These remain migration anchors, not the target-state secret ownership model.

Current-to-target logical mapping examples:

| Current legacy secret surface | Target logical destination |
|---|---|
| `vault_control_plane_backend_*` | `platform::kv-apps/data/control-plane/backend` |
| `vault_control_plane_worker_*` | `platform::kv-apps/data/control-plane/task-worker` |
| `vault_control_plane_manifest_signing_key` | `platform::kv-apps/data/control-plane/helix-adapter` |
| `vault_control_plane_registry_*` | `platform::kv-shared/data/registry/ghcr` |
| `vault_control_plane_helix_internal_auth_token` | `platform::kv-shared/data/helix/shared-auth` |
| `vault_control_plane_helix_remnawave_token` | `platform::kv-shared/data/integration/remnawave` |

Rules:

1. The current Ansible-vault bootstrap path is legacy and migration-scoped.
2. New platform services must not introduce additional long-lived `.env`-file secret sprawl.
3. Migration from current legacy keys into OpenBao must preserve ownership boundaries rather than mirror current file layout blindly.

## 12. Adoption Rules

Effective immediately:

1. New platform docs must refer to `openbao-prod` and `openbao-nonprod`.
2. New auth-mount examples must use the frozen naming patterns from this registry.
3. New PKI plans must use `pki-k8s`, `pki-infra`, and reserved `pki-fleet`.
4. New bootstrap designs must explicitly say whether they use `JWT`, `OIDC`, `cert`, or a documented AppRole exception.
5. No new design may treat `.env` files or static inventory secrets as the future source of truth for platform secrets.
