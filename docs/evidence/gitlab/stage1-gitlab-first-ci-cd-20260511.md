# Stage 1 GitLab First CI/CD Evidence

Date: 2026-05-11

Scope: switch repository operations to GitLab-first, keep GitHub as fallback, and align Stage 1 limited-publication CI/CD gates.

## Decision

Owner decision:

```text
GitLab is first for repository CI/CD and release evidence.
GitHub remains the external fallback remote.
```

This does not make the home GitLab server a customer-runtime dependency. Stage 1 customer availability, payment webhooks, Telegram webhooks, VPN node availability and emergency rollback must not depend only on the home server.

## Local Remote Model

Target remotes:

```text
origin = https://gitlab.h.cyber-vpn.net/root/CyberVPN.git
github = https://github.com/Beep206/CyberVPN.git
```

Push order:

```text
1. push main to origin/GitLab
2. verify GitLab accepts commit and pipeline starts
3. push same commit to github/GitHub
```

Credentials must not be stored in `.git/config`. Temporary Git credential/askpass flow is allowed for the push as long as no token/password is printed to logs or committed.

## CI/CD Alignment

The GitLab pipeline includes:

- path-gated validation/lint/test/build jobs for the monorepo workspaces;
- protected-runner default tag `h-docker`;
- security jobs for secret scan, gitleaks wrapper, npm audit, pip audit, filesystem vulnerability scans and SBOM;
- manual Docker build jobs isolated behind `dind`;
- no automatic `docker push`;
- no production secrets;
- no automatic production deployment;
- manual `stage1:limited-publication-preflight` job.
- explicit `STAGE1_FULL_CI=true` switch for a full Stage 1 validation pass when path-gated jobs would otherwise skip unchanged workspaces.
- explicit `STAGE1_LIMITED_PUBLICATION_PREFLIGHT=true` switch for a preflight-only pipeline; normal path-gated app, security, observability and future-stage jobs are skipped so limited-publication checks stay fast and deterministic.
- Gitleaks runs from an allowed `alpine:3.20` job image and downloads a pinned binary with checksum verification; the home runner does not need to allow arbitrary `ghcr.io/gitleaks/*` images.
- Grype filesystem scan is bounded by `GRYPE_SCAN_TIMEOUT_SECONDS` and `GRYPE_SCAN_ATTEMPTS`; Trivy remains the required filesystem vulnerability evidence unless `PHASE20_GRYPE_REQUIRED=true` is explicitly enabled later.
- Stage 2 observability and Stage 3 partner artifact validators are advisory during Stage 1 and must not block controlled public beta publication.
- Partner portal app jobs are advisory during Stage 1 because partner portal belongs to Stage 3, not the controlled public beta B2C path.
- Backend Stage 1 CI blocks on `ruff check`; full `ruff format --check src/` is deferred until the existing formatter baseline is normalized outside the limited publication path.
- Backend smoke tests use CI-only placeholder `REMNAWAVE_TOKEN`, `JWT_SECRET`, and `CRYPTOBOT_TOKEN` values so Settings can initialize without importing production secrets into GitLab.
- Backend smoke tests run with `--no-cov`; repository-wide coverage belongs in a separate coverage gate, not in a narrow Stage 1 smoke job.
- Task-worker lint and smoke jobs are advisory until its existing ruff baseline is normalized; Stage 1 worker readiness is still controlled through runtime smoke/evidence gates.
- Next.js workspace apps set `turbopack.root` to the monorepo root so GitLab CI can resolve hoisted Next packages during builds.
- Frontend Next.js builds limit CI CPU/static generation concurrency under `CI=true`; this avoids runner OOM kills while preserving normal local/runtime behavior.

The `stage1:limited-publication-preflight` job:

- is manual;
- prepares the GitLab environment `stage1/limited-public-beta`;
- curls public Stage 1 endpoints;
- writes a CI artifact under `docs/evidence/releases/ci-stage1/`;
- reads the latest stabilization evidence if present;
- fails only when `STAGE1_REQUIRE_BETA_GO=true` and latest stabilization evidence still says external beta is `NO-GO`.

This lets GitLab become the first CI/CD gate while preserving the current launch blockers.

## Validation

Local contract:

```text
python scripts/validate_gitlab_ci_contract.py
PASS: GitLab CI contract is ready for initial GitLab import
```

Security model:

```text
real production payment, Telegram, Remnawave, database, JWT/TOTP/OAuth and SSH private secrets are not required in GitLab CI for this step
```

## Remaining Before Limited User Publishing

GitLab-first CI/CD can start now, but external beta users remain blocked until:

1. sensitive GitLab runner request-header logging is redacted in Caddy/Loki;
2. an approved immutable snapshot/tag is created;
3. a production VPN node is proven;
4. trial provisioning works on the production node;
5. one payment path is proven if paid beta is included;
6. support mailbox or Telegram-only first-cohort support is proven.
