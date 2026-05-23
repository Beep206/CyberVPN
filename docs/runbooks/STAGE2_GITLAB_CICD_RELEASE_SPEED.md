# Stage 2 GitLab CI/CD And Release Speed Runbook

**Stage:** `S2-STAGE-14`
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. Rule

GitLab is first.

GitHub remains the mirror/fallback.

Production deploy is manual unless the owner explicitly enables one service for auto-deploy after clean S2 history.

---

## 2. Normal Commit Flow

```bash
git status --short
git add <changed-files>
git commit -m "<message>"
```

Push GitLab first:

```bash
GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ProxyCommand='ssh -o BatchMode=yes beep@10.10.10.34 -W 127.0.0.1:2222'" \
git push ssh://git@gitlab-local/root/CyberVPN.git main
```

Verify GitLab ref:

```bash
GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ProxyCommand='ssh -o BatchMode=yes beep@10.10.10.34 -W 127.0.0.1:2222'" \
git ls-remote ssh://git@gitlab-local/root/CyberVPN.git refs/heads/main
```

Push GitHub mirror:

```bash
git push github main
git ls-remote github refs/heads/main
```

Expected: both refs point to the same SHA.

---

## 3. GitLab Jobs To Use

| Situation | Jobs |
|---|---|
| Frontend/Mini App fix | `frontend:lint`, `frontend:test`, `frontend:build`, `stage2:release-evidence-pack`, `stage2:deploy:dry-run`, then manual `stage1:deploy:frontend` |
| Admin fix | `admin:lint`, `admin:test`, `admin:build`, `stage2:release-evidence-pack`, `stage2:deploy:dry-run`, then manual `stage1:deploy:admin` |
| Backend fix | `backend:lint`, `backend:test:smoke`, security jobs if sensitive, `stage2:deploy:dry-run`, then manual `stage1:deploy:backend` |
| Telegram bot fix | `telegram-bot:lint`, `telegram-bot:test:smoke`, `stage2:deploy:dry-run`, then manual `stage1:deploy:telegram-bot` |
| Worker/scheduler fix | `task-worker:lint`, `task-worker:test:smoke`, `stage2:deploy:dry-run`, then manual `stage1:deploy:task-worker` |
| Release candidate | relevant path jobs, security jobs, `stage2:release-evidence-pack`, `stage2:deploy:dry-run`, release rehearsal |

Deploy jobs still use `stage1:*` names because the rented production compose stack is still the Stage 1 runtime stack. S2 changes the release posture, not the compose service names.

---

## 4. S2 Evidence Job

Run:

```text
stage2:release-evidence-pack
```

Artifact:

```text
docs/evidence/releases/ci-stage2/stage2-release-evidence-<short-sha>.md
```

It records:

- commit SHA;
- GitLab ref;
- pipeline URL;
- changed files;
- S2 release tag input;
- dry-run service input;
- GitHub mirror requirement.

---

## 5. Deploy Dry-Run

Run:

```text
stage2:deploy:dry-run
```

Useful variables:

```text
S2_RELEASE_TAG=stage2-public-rc.1
S2_DRY_RUN_SERVICES=frontend
```

Allowed service values:

```text
all
frontend
admin
backend
telegram-bot
task-worker
```

The dry-run calls:

```bash
STAGE1_DEPLOY_DRY_RUN=true \
STAGE1_DEPLOY_EVIDENCE_DIR=docs/evidence/releases/ci-stage2 \
STAGE1_RELEASE_TAG="${S2_RELEASE_TAG:-s2-ci-${CI_PIPELINE_IID}-${CI_COMMIT_SHORT_SHA}}" \
bash scripts/deploy/stage1-gitlab-deploy.sh "${S2_DRY_RUN_SERVICES:-frontend}"
```

Expected:

- service list accepted;
- release tag accepted;
- evidence written;
- no SSH;
- no rsync;
- no Docker build;
- no compose restart;
- no public smoke.

---

## 6. Real Deploy

Run only after relevant jobs and dry-run pass.

Service-specific deploy jobs:

```text
stage1:deploy:frontend
stage1:deploy:admin
stage1:deploy:backend
stage1:deploy:telegram-bot
stage1:deploy:task-worker
```

Full deploy:

```text
stage1:deploy:all
```

Keep full deploy manual.

Use immutable release identity:

```text
STAGE1_RELEASE_TAG=stage2-public-rc.N
```

Do not deploy floating `main`.

---

## 7. Hotfix Path

If GitLab is online:

1. push to GitLab;
2. wait for relevant jobs;
3. run dry-run;
4. run manual service deploy;
5. validate public flow;
6. push GitHub mirror.

If GitLab is offline and the issue is urgent:

1. use GitHub/local repo as source fallback;
2. deploy directly to `prod-app-1` using the existing production deploy procedure;
3. record emergency evidence;
4. push/merge the exact resulting commit back to GitLab when it returns;
5. run the skipped CI jobs retroactively.

---

## 8. Rollback

Rollback must not depend on GitLab.

On `prod-app-1`:

1. find last known good `CYBERVPN_IMAGE_TAG`;
2. update compose `.env`;
3. run `docker compose up -d <affected-services>`;
4. run public smoke;
5. record rollback evidence.

Use the Stage 2 backup/DR runbook for DB or data incidents.

---

## 9. Variables

Required for real production deploy:

```text
STAGE1_PROD_HOST
STAGE1_PROD_USER
STAGE1_PROD_SSH_PRIVATE_KEY or STAGE1_PROD_SSH_KEY_FILE
STAGE1_PROD_KNOWN_HOSTS
```

Stage 2 release-speed variables:

```text
STAGE2_RELEASE_SPEED=true
S2_RELEASE_TAG=stage2-public-rc.N
S2_DRY_RUN_SERVICES=frontend
```

No key rotation is required by this stage. Rotate only after suspected disclosure, lost operator device, runner compromise or explicit owner decision.

---

## 10. No-Go Conditions

Do not run production deploy if:

1. GitLab and GitHub refs disagree unexpectedly;
2. relevant path-gated jobs failed;
3. `stage2:deploy:dry-run` failed;
4. release tag is missing or mutable;
5. deploy would touch unrelated services without owner approval;
6. rollback target is unknown;
7. production backup is stale before a risky DB/data change.

---

## 11. Next Stage

```text
S2-STAGE-15: Full Staging/Public-Release Rehearsal
```
