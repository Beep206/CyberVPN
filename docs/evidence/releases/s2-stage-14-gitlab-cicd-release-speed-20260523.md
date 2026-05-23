# S2-STAGE-14 GitLab CI/CD And Release Speed Evidence

**Date:** 2026-05-23
**Stage:** `S2-STAGE-14`
**Result:** `PASS_WITH_CONTROLLED_GAPS`
**Owner:** `@Sasha_Beep`

---

## 1. Scope

This evidence records the Stage 2 GitLab-first CI/CD and release-speed gate.

Covered:

- GitLab/GitHub synchronized baseline;
- GitLab Runner health;
- GitLab CI contract validation;
- S2 release evidence job;
- S2 deploy dry-run job;
- no-network deploy dry-run proof;
- manual deploy safety;
- immutable release tag policy;
- GitHub fallback and direct rollback model.

No production secret values are stored in this file.

---

## 2. Baseline Remotes

Before this stage:

```text
GitLab main d6d8d1d9c76929b429e59c840a0828bbbef9929c
GitHub main d6d8d1d9c76929b429e59c840a0828bbbef9929c
```

Interpretation:

```text
GitLab and GitHub were synchronized before the S2-STAGE-14 patch.
```

---

## 3. GitLab Runner Health

Home server:

```text
host=cybervpn-h-ops
```

Observed containers:

```text
cybervpn-gitlab          Up 2 days (healthy)
cybervpn-gitlab-runner   Up 12 days
```

Runner:

```text
GitLab Runner version 18.11.2
Executor docker
Runner name cybervpn-h-docker-protected
```

The raw runner token was not recorded in this evidence.

---

## 4. CI/CD Changes

Added to `.gitlab-ci.yml`:

```text
.rules_stage2_release_speed
stage2:release-evidence-pack
stage2:deploy:dry-run
```

Added deploy script support:

```text
STAGE1_DEPLOY_DRY_RUN=true
```

Updated local contract validator:

```text
scripts/validate_gitlab_ci_contract.py
```

---

## 5. Local CI Contract Proof

Command:

```text
python scripts/validate_gitlab_ci_contract.py
```

Observed:

```text
PASS: GitLab CI contract is ready for initial GitLab import
```

The contract now requires:

- Stage 2 release-speed rules;
- `stage2:release-evidence-pack`;
- `stage2:deploy:dry-run`;
- `docs/evidence/releases/ci-stage2/`;
- immutable S2 release tag markers;
- deploy dry-run support.

---

## 6. Deploy Dry-Run Proof

Command:

```text
STAGE1_DEPLOY_DRY_RUN=true
STAGE1_DEPLOY_EVIDENCE_DIR=.tmp/s2-stage14-dry-run
STAGE1_RELEASE_TAG=s2-ci-local-dry-run
bash scripts/deploy/stage1-gitlab-deploy.sh frontend
```

Observed evidence:

```text
Release tag: s2-ci-local-dry-run
Commit: local
Pipeline: local
Services: frontend
Host: dry-run.invalid
Compose dir: /srv/cybervpn/compose/app
Release root: /srv/cybervpn/releases
Image registry: cybervpn
Dry run: true
No SSH, rsync, Docker build, compose restart or public smoke was executed.
```

Interpretation:

```text
The deploy contract can be validated in GitLab without production access or runtime impact.
```

---

## 7. Release-Speed Model

Normal S2 frontend fix path:

```text
GitLab push
frontend lint/test/build
stage2:release-evidence-pack
stage2:deploy:dry-run
manual stage1:deploy:frontend
public smoke
GitHub mirror push
```

Backend, bot, admin and worker follow the same pattern with their service-specific test and deploy jobs.

Expected benefit:

```text
Small fixes no longer require repeated local packaging and manual server copy for every correction.
```

---

## 8. Safety Boundaries

Preserved:

- production deploy jobs are manual;
- `stage1:deploy:all` remains manual;
- deploys use `resource_group: stage1-production`;
- GitHub remains fallback;
- customer runtime does not depend on home GitLab;
- emergency rollback remains direct on `prod-app-1`;
- VPN node remains node-only;
- HTTP/3/QUIC must not be disabled by deploy steps.

No key rotation is required by this stage because no new production key or secret is introduced by the CI/CD patch.

---

## 9. Controlled Gaps

| Gap | Accepted for S2? | Follow-up |
|---|---|---|
| Real GitLab pipeline for this patch runs after push | Yes | Confirm pipeline before `S2-STAGE-15` |
| Stage 2 deploy still reuses `stage1:*` deploy job names | Yes | Rename only when runtime compose/deploy stack is renamed |
| Docker images are still built on production host by deploy script | Yes for current cost constraints | Move to registry digest-pinned image promotion when budget/runner capacity allows |
| GitLab is home-hosted | Yes | Keep GitHub fallback and direct rollback |
| Auto-deploy is not enabled | Yes | Enable only per service after clean S2 deploy history |

---

## 10. Local Validation

Commands run during this gate:

```text
python scripts/validate_gitlab_ci_contract.py -> PASS
python YAML parse for .gitlab-ci.yml -> YAML parse ok
bash -n scripts/deploy/stage1-gitlab-deploy.sh -> PASS
STAGE1_DEPLOY_DRY_RUN=true ... stage1-gitlab-deploy.sh frontend -> PASS
cd backend && uv run pytest --no-cov tests/contract/test_stage2_gitlab_cicd_release_speed_contract.py -> 4 passed
git diff --check -> PASS
```

Security review checks:

```text
scripts/security/scan-secrets.sh -> no leaks found
scripts/security/audit-dependencies.sh npm -> root/admin/frontend/partner exit_code=0 at high threshold
dangerous-pattern scan over changed CI/deploy/test files -> no matches
secret-name scan over changed docs/CI/deploy/test files -> variable names/placeholders only, no secret values
```

---

## 11. Result

`S2-STAGE-14` passes with controlled gaps.

GitLab remains first, GitHub remains fallback, and Stage 2 now has an explicit CI release evidence job plus no-network deploy dry-run validation before real manual deploys.

Next stage:

```text
S2-STAGE-15: Full Staging/Public-Release Rehearsal
```
