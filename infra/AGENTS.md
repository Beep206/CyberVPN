# CyberVPN Infrastructure Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file explicitly before changing `infra/`, deployment workflows, runtime
configuration, or infrastructure scripts.

## Environment classification

Before any action, classify the target as local, test, staging, or production
and record the account/cluster/namespace/project/region when applicable.

- Local and disposable test infrastructure may be installed, started, reset,
  and repaired autonomously.
- Staging changes must use the repository's normal plan/deploy path and preserve
  rollback.
- Production deployment, production data mutation, secret rotation, destructive
  state operations, DNS changes, certificate changes, and irreversible cloud
  actions require explicit task scope.
- Never infer production scope from available credentials.

## Infrastructure as code

- Treat checked-in Compose, Terraform, Helm/Kubernetes, workflow, and service
  definitions as the canonical configuration.
- Do not make an unrecorded manual change as a substitute for code.
- Keep changes idempotent, reviewable, reproducible, and environment-parameterized.
- Pin action, image, chart, module, package, and tool versions according to the
  existing repository policy. Do not introduce floating `latest` tags.
- Preserve remote-state locking, encryption, backup, retention, and recovery
  behavior.
- Use least-privilege identities, narrow network policies, read-only filesystems
  where practical, dropped capabilities, non-root users, and explicit
  filesystem permissions.
- Define health/readiness/startup checks that measure real service state without
  mutating it.
- Set CPU, memory, storage, connection, queue, timeout, retry, and rollout
  bounds.
- Keep deployment ordering, migration ownership, rollback, and compatibility
  with the previous application version explicit.

## Secrets and configuration

- Never commit real secrets, credentials, private keys, tokens, kubeconfigs,
  state files, `.env` contents, or provider payloads.
- Use secret-manager/environment references and safe `.example` files.
- Do not print secrets through shell tracing, workflow output, plan output,
  Docker build logs, crash artifacts, or generated manifests.
- Separate build-time public configuration from runtime secrets.
- Validate required configuration at startup with safe error messages.
- Rotation changes require overlap/rollback behavior and consumer validation.

## Networking and data safety

- Minimize public exposure and inbound/outbound rules.
- Preserve TLS verification; do not add insecure skips for convenience.
- Validate proxy, redirect, CORS, trusted-host, and forwarded-header behavior.
- Database/cache/broker changes require backup/restore, migration ordering,
  compatibility, and failure-mode analysis.
- Destructive operations need an explicit target and a dry-run/plan when the
  tool supports one.
- Never use wildcard deletion or broad recursive paths derived from untrusted
  variables.

## CI/CD

- Required checks must fail closed. Do not add `continue-on-error`, `|| true`,
  skipped jobs, or permissive conditions around release-critical validation.
- Use minimum workflow permissions and pinned trusted actions.
- Separate pull-request validation, artifact publication, promotion, and
  deployment.
- Build once and promote the same verified artifact where the release process
  supports it.
- Record provenance, checksums/signatures, SBOM, release version, environment,
  and rollback information when required.
- Never claim deployment or CI success without reading the actual job status
  and relevant logs.

## Validation

Run every applicable native validator after the final change:

- `shellcheck` for changed shell scripts;
- `docker compose config` and service/image health smoke for Compose;
- `terraform fmt -check`, `validate`, and a reviewed plan for Terraform;
- `helm lint/template` plus schema/policy validation for Helm;
- client-side/server-side dry run and policy validation for Kubernetes;
- workflow syntax/action validation for CI;
- container build, vulnerability/config scan, and non-root/health smoke;
- deployment dry run and rollback evidence for release changes.

Use WSL Ubuntu 24.04/Linux commands for local execution, while preserving
portable scripts and target-platform behavior required by the repository.
Validation of syntax alone is not proof of a working deployment.
