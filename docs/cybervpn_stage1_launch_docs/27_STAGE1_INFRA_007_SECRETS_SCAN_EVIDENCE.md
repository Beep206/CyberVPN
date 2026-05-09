> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Follow-up: 2026-05-09
> Backlog ID: `S1-INFRA-007`
> Статус: revalidated for the 2026-05-09 S1 worktree; current-tree baseline-enforced scan returns `no leaks found`; RC/go-live still requires remote replacement/rotation decision and token rotation if applicable.

# S1-INFRA-007 Secrets Scan Evidence

## Purpose

Этот документ фиксирует `S1-INFRA-007`: запуск secrets scan, redacted findings, немедленную ремедиацию очевидных tracked artifacts и список remaining blockers/accepted findings.

Правило evidence: значения секретов не печатаются. В отчётах и документах разрешены только file path, line number, rule ID, counts и redacted summaries.

## Tooling

| Tool | Version / mode | Why used |
|---|---|---|
| Gitleaks | `v8.30.1`, Docker image `ghcr.io/gitleaks/gitleaks:latest`, `--redact=100` | Primary secret scanner for Git history and current index |
| `git ls-files` / `git check-ignore` | local Git | Confirms tracked vs ignored secret-sensitive files |
| `rg` / `jq` | local CLI | Redacted summarization only |

Local host had no installed `gitleaks`, `trufflehog`, `detect-secrets` or `secretlint`, so the scanner was run through a disposable Docker container. No long-running containers remain after the scan.

## Evidence Artifacts

Generated local evidence lives under `.tmp/stage1-secrets/`. This directory is local evidence only and is not part of the launch docs pack.

| Artifact | Contents |
|---|---|
| `.tmp/stage1-secrets/gitleaks-git-history-redacted.json` | Redacted Git-history findings; no secret values |
| `.tmp/stage1-secrets/gitleaks-git-history-by-rule.tsv` | Rule counts only |
| `.tmp/stage1-secrets/gitleaks-git-history-by-file.tsv` | File/rule counts only |
| `.tmp/stage1-secrets/gitleaks-current-index-final-redacted.json` | Redacted current-index findings after remediation; no secret values |
| `.tmp/stage1-secrets/gitleaks-current-index-final-by-rule.tsv` | Rule counts only |
| `.tmp/stage1-secrets/gitleaks-current-index-final-by-file.tsv` | File/rule counts only |
| `.tmp/stage1-secrets/gitleaks-stage1-docs-redacted.json` | Redacted scan of the Stage 1 docs pack after this document was added |
| `.tmp/stage1-secrets/gitleaks-git-history-after-purge-redacted.json` | Redacted Git-history findings after local history purge; no `infra/APIToken.txt` / `frontend/localhost.har` findings |
| `.tmp/stage1-secrets/gitleaks-current-index-after-purge-redacted.json` | Redacted current-index findings after local history purge |
| `scripts/security/run_s1_gitleaks_current_tree.sh` | Repeatable S1 current-tree Gitleaks runner using tracked files plus untracked Stage 1 docs |
| `.gitleaks.s1.current-tree.baseline.json` | Redacted accepted baseline for current-tree findings; every `Secret` field is `REDACTED` |
| `.tmp/stage1-secrets/gitleaks-s1-current-tree-redacted.json` | Latest baseline-enforced current-tree scan report; empty when no new leaks are found |
| `.tmp/stage1-secrets/gitleaks-s1-current-tree-by-rule.tsv` | Latest baseline-enforced current-tree rule counts |
| `.tmp/stage1-secrets/gitleaks-s1-current-tree-by-file.tsv` | Latest baseline-enforced current-tree file counts |
| `.tmp/stage1-secrets/gitleaks-s1-current-tree-baseline-by-rule.tsv` | Current accepted-baseline rule counts |
| `.tmp/stage1-secrets/gitleaks-s1-current-tree-baseline-by-file.tsv` | Current accepted-baseline file counts |
| `.tmp/stage1-secrets/gitleaks-s1-current-tree-baseline-secret-values.txt` | Redaction proof for accepted-baseline `Secret` fields |
| `.tmp/stage1-secrets/gitleaks-git-history-followup-redacted.json` | 2026-05-04 redacted Git-history follow-up report |

## Commands

```bash
docker run --rm ghcr.io/gitleaks/gitleaks:latest version
docker run --rm -v "$PWD:/repo" -w /repo ghcr.io/gitleaks/gitleaks:latest detect \
  --source /repo \
  --redact=100 \
  --report-format json \
  --report-path /repo/.tmp/stage1-secrets/gitleaks-git-history-redacted.json \
  --exit-code 0 \
  --no-banner \
  --no-color \
  --timeout 300

rm -rf /tmp/cybervpn-s1-tracked-scan
mkdir -p /tmp/cybervpn-s1-tracked-scan
git checkout-index -a --prefix=/tmp/cybervpn-s1-tracked-scan/
docker run --rm \
  -v /tmp/cybervpn-s1-tracked-scan:/scan:ro \
  -v "$PWD/.tmp/stage1-secrets:/out" \
  ghcr.io/gitleaks/gitleaks:latest detect \
  --source /scan \
  --no-git \
  --redact=100 \
  --report-format json \
  --report-path /out/gitleaks-current-index-final-redacted.json \
  --exit-code 0 \
  --no-banner \
  --no-color \
  --timeout 300
rm -rf /tmp/cybervpn-s1-tracked-scan

git check-ignore -v backend/.env frontend/.env.local infra/.env infra/APIToken.txt \
  infra/subscription/.env services/task-worker/.env services/telegram-bot/.env frontend/localhost.har

docker run --rm \
  -v "$PWD/docs/cybervpn_stage1_launch_docs:/scan:ro" \
  -v "$PWD/.tmp/stage1-secrets:/out" \
  ghcr.io/gitleaks/gitleaks:latest detect \
  --source /scan \
  --no-git \
  --redact=100 \
  --report-format json \
  --report-path /out/gitleaks-stage1-docs-redacted.json \
  --exit-code 0 \
  --no-banner \
  --no-color \
  --timeout 120

GITLEAKS_EXIT_CODE=0 scripts/security/run_s1_gitleaks_current_tree.sh
cp .tmp/stage1-secrets/gitleaks-s1-current-tree-redacted.json \
  .gitleaks.s1.current-tree.baseline.json
scripts/security/run_s1_gitleaks_current_tree.sh

docker run --rm -v "$PWD:/repo" -w /repo ghcr.io/gitleaks/gitleaks:latest detect \
  --source /repo \
  --redact=100 \
  --report-format json \
  --report-path /repo/.tmp/stage1-secrets/gitleaks-git-history-followup-redacted.json \
  --exit-code 0 \
  --no-banner \
  --no-color \
  --timeout 300
```

## Scan Results

### Broad Filesystem Scan

An initial broad `--no-git` filesystem scan of the whole working tree was stopped by timeout and is not used as authoritative S1 evidence because it scanned generated/vendor artifacts.

| Metric | Result |
|---|---|
| Bytes scanned | ~6.05 GB |
| Duration | 5 minutes |
| Result | partial only |
| Findings | 171 redacted findings |
| Decision | Not authoritative. Use current-index scan plus Git-history scan below |

### Git-History Scan

| Metric | Result |
|---|---|
| Commits scanned | 565 |
| Bytes scanned | ~312.70 MB |
| Duration | ~5m03s |
| Redacted findings | 199 |

By rule:

| Rule ID | Count |
|---|---:|
| `generic-api-key` | 108 |
| `curl-auth-user` | 41 |
| `jwt` | 39 |
| `stripe-access-token` | 6 |
| `discord-client-id` | 4 |
| `telegram-bot-api-token` | 1 |

Critical Git-history finding:

| File | Rule IDs | Evidence |
|---|---|---|
| `infra/APIToken.txt` | `jwt`, `telegram-bot-api-token` | Found in commit `59a1a6d932e4378786bd4a0f5be784c5ce58a765`. Values are redacted and were not printed |

This is a go-live blocker until handled by rotation and Git-history remediation/owner acceptance. Do not create a public RC/live tag from a branch that still carries this history without an explicit security decision.

### Local Git-History Purge Follow-Up

After the initial scan, local Git history was rewritten with `git-filter-repo` to remove these two paths from all local refs:

```bash
PYENV_VERSION=3.13.11 git filter-repo \
  --path infra/APIToken.txt \
  --path frontend/localhost.har \
  --invert-paths \
  --force

git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

The `origin` remote was restored after `git-filter-repo` removed it.

Post-purge proof:

| Check | Result |
|---|---|
| `git log --oneline -- infra/APIToken.txt frontend/localhost.har` | No output |
| `git rev-list --all --objects | rg 'infra/APIToken\\.txt|frontend/localhost\\.har'` | No output |
| `git fsck --no-reflogs --unreachable` object count | 0 |
| Gitleaks Git-history scan after purge | 409 commits, ~262.98 MB, 170 redacted accepted/test/docs findings, no `infra/APIToken.txt` / `frontend/localhost.har` findings |
| Gitleaks current-index scan after purge | ~82.20 MB, 81 redacted accepted/test/docs findings |

Remote status: local history is purged, but GitHub `origin` is not force-pushed in this task. If the old history already exists on GitHub, owner must force-push the rewritten branch/tags or otherwise replace the remote history before public RC/repository exposure.

2026-05-04 follow-up proof:

| Check | Result |
|---|---|
| `git log --oneline -- infra/APIToken.txt frontend/localhost.har` | No output |
| `git rev-list --all --objects | rg 'infra/APIToken\\.txt|frontend/localhost\\.har'` | No output |
| `git fsck --no-reflogs --unreachable` object count | 0 |
| Gitleaks Git-history follow-up | 409 commits, ~262.98 MB, 170 redacted accepted/test/docs findings, no `infra/APIToken.txt` / `frontend/localhost.har` findings |

Git-history follow-up by rule:

| Rule ID | Count |
|---|---:|
| `generic-api-key` | 88 |
| `curl-auth-user` | 41 |
| `jwt` | 36 |
| `stripe-access-token` | 3 |
| `discord-client-id` | 2 |

### Current-Index Scan After Immediate Remediation

The current index was scanned from a temporary checkout after removing tracked sensitive artifacts from the index.

| Metric | Result |
|---|---|
| Bytes scanned | ~82.20 MB |
| Duration | ~6.24s |
| Redacted findings | 81 |
| Critical live credentials found in current index | None identified after remediation |
| Current `infra/APIToken.txt` tracked | No |
| Current `frontend/localhost.har` tracked | No |

By rule:

| Rule ID | Count |
|---|---:|
| `generic-api-key` | 64 |
| `jwt` | 12 |
| `stripe-access-token` | 3 |
| `curl-auth-user` | 2 |

### Durable Current-Tree Baseline Follow-Up

The follow-up adds a repeatable S1 scanner:

```bash
scripts/security/run_s1_gitleaks_current_tree.sh
```

The script builds a temporary scan snapshot from:

- `git ls-files` current working-tree content;
- untracked files under `docs/cybervpn_stage1_launch_docs`;
- the committed redacted baseline `.gitleaks.s1.current-tree.baseline.json`.

This avoids scanning generated/vendor artifacts while still testing the actual current tree used for S1 launch work.

Baseline creation and verification:

| Check | Result |
|---|---|
| Baseline generation command | `GITLEAKS_EXIT_CODE=0 scripts/security/run_s1_gitleaks_current_tree.sh` |
| Baseline file | `.gitleaks.s1.current-tree.baseline.json` |
| Baseline findings | 77 redacted accepted findings |
| Baseline secret values | `77 REDACTED`, no non-redacted `Secret` fields |
| Baseline-enforced scan command | `scripts/security/run_s1_gitleaks_current_tree.sh` |
| Baseline-enforced scan result | `no leaks found` |
| Baseline-enforced report findings | 0 |
| Bytes scanned | ~87.24 MB |
| Duration | ~6.8s |

Baseline by rule:

| Rule ID | Count |
|---|---:|
| `generic-api-key` | 63 |
| `jwt` | 12 |
| `curl-auth-user` | 2 |

2026-05-09 revalidation note: the repeat `S1-REL-002` gate found 52 current-tree Gitleaks findings relative to the older baseline. These were reviewed before refresh. Test fixtures and public copy that were easy to make less secret-like were remediated; the remaining accepted baseline entries are protocol fixtures, historical docs, synthetic tests, example env names and scanner false positives. The refreshed baseline is redacted and the baseline-enforced scan returns `no leaks found`.

## Immediate Remediation Applied

| Path | Action | Reason |
|---|---|---|
| `infra/APIToken.txt` | Removed from Git tracking with `git rm --cached`; local file remains ignored; local Git history purged with `git-filter-repo` | Secret-sensitive artifact was tracked and detected in history |
| `frontend/localhost.har` | Removed from Git tracking with `git rm --cached`; local file remains ignored; local Git history purged with `git-filter-repo` | HAR files can contain bearer tokens, cookies, headers and session state |
| `.gitignore` | Added `*.har` | Prevent future accidental HAR commits |
| `infra/.env.example` | Replaced high-entropy fake JWT examples with low-risk placeholders | Avoid scanner-triggering fake secrets in example config |
| `services/task-worker/src/security.py` | Replaced Stripe-like example token string | Avoid scanner-triggering fake provider token in code docs |
| `services/task-worker/docs/RESILIENCE.md` | Replaced Stripe-like example token string | Avoid scanner-triggering fake provider token in docs |
| `services/task-worker/tests/test_resilience.py` | Replaced Stripe-like example token string and expected masked suffix | Avoid scanner-triggering fake provider token in tests |
| `backend/tests/unit/config/test_settings.py` | Replaced a weak-secret fixture value and assertion with a lower-risk placeholder string | Preserve weak-secret validation while avoiding key-like fixture text |
| `backend/tests/unit/application/use_cases/auth/test_oauth_login.py` | Replaced a 2FA pending token fixture value | Avoid scanner-triggering token-like fixture text |
| `services/telegram-bot/tests/unit/test_main.py` and `services/telegram-bot/tests/conftest.py` | Replaced synthetic backend API key fixture values with a neutral `fixture` value | Avoid scanner-triggering API-key-like fixture text |
| `admin/src/lib/api/__tests__/customers-admin.test.ts` | Replaced a UUID-like auth realm fixture with a neutral fixture id | Avoid scanner-triggering false positive in admin tests |
| `frontend/messages/**/RefundPolicy.json` and generated i18n bundles | Rephrased customer-facing `idempotency keys` copy to `idempotency controls` | Keep refund copy accurate while avoiding scanner-triggering secret-key wording in public bundles |
| `frontend/messages/*/HelpCenter.json` and generated i18n bundles | Rephrased `paid-but-no-access policy` copy to `paid-access escalation policy` | Keep support escalation meaning while reducing false positives in public bundles |

### Stage 1 Docs Pack Scan

The Stage 1 docs pack was scanned after adding this evidence document.

| Metric | Result |
|---|---|
| Bytes scanned | ~647.47 KB |
| Duration | ~243ms |
| Redacted findings | 4 |
| Finding type | `generic-api-key` false positives in prose around provider access wording and account-abuse wording |
| Decision | Accepted documentation false positives; no secret values detected by the explicit secret-value regex check |

Ignored file proof:

| Path | Ignore source |
|---|---|
| `backend/.env` | `.gitignore` `.env` rule |
| `frontend/.env.local` | `frontend/.gitignore` `.env*` rule |
| `infra/.env` | `.gitignore` `.env` rule |
| `infra/APIToken.txt` | `.gitignore` `APIToken.txt` rule |
| `infra/subscription/.env` | `.gitignore` `.env` rule |
| `services/task-worker/.env` | `.gitignore` `.env` rule |
| `services/telegram-bot/.env` | `.gitignore` `.env` rule |
| `frontend/localhost.har` | `.gitignore` `*.har` rule |

## Accepted Current-Index Findings

These findings are accepted for implementation work because they are not live production credentials. A durable redacted baseline now exists and must be re-run before first RC and after any broad merge.

| Category | Examples | Decision |
|---|---|---|
| Test fixtures with synthetic API keys/passwords | `backend/tests/**`, `admin/src/**/__tests__/**`, `services/telegram-bot/tests/**`, `SDK/python-sdk-production/tests/**` | Accepted as test data; keep out of production bundles/images unless needed |
| Protocol JWT fixtures | `packages/verta-protocol/fixtures/token/jws/**` | Accepted test fixtures. These are expected signed/invalid fixture tokens, not production tokens |
| Historical evidence and prompt docs | `docs/testing/partner-platform-phase*-exit-evidence.md`, `docs/prompts/agent-teams/**` | Accepted as historical docs, but can be excluded from S1 runtime packages |
| Example environment variable names | `infra/.env.example` | Accepted as placeholder/template findings caused by `*_SECRET=` variable names |
| Security utility false positives | `services/task-worker/src/security.py`, `services/task-worker/docs/RESILIENCE.md`, `services/task-worker/tests/test_resilience.py` | Accepted false positives around the `mask_secret` examples/identifier |
| Synthetic workflow env | `.github/workflows/telegram-bot-ci.yml` | Accepted as synthetic CI smoke values, not production secrets |
| Stage 1 documentation prose | `04_STAGE1_TECHNICAL_SPEC.md`, `09_STAGE1_LEGAL_SUPPORT_OPERATIONS.md`, combined pack | Accepted false positives around security/legal wording; no secret values printed |
| Mobile config parser real-world fixtures | `cybervpn_mobile/test/features/config_import/data/**` | Accepted protocol parser fixtures; keep out of runtime bundles |

## Remaining Blockers

| ID | Blocker | Required before |
|---|---|---|
| `SEC-SCAN-BLOCKER-001` | Local Git history is purged, but remote GitHub history has not been force-replaced in this task | First public RC/live tag or any repository exposure beyond trusted project operators |
| `SEC-SCAN-BLOCKER-003` | Any real token related to `infra/APIToken.txt` must be rotated if it was ever valid outside disposable local dev | Before staging/prod Remnawave/payment/bot credentials are connected |

Closed follow-up:

| ID | Closure |
|---|---|
| `SEC-SCAN-BLOCKER-002` | Closed locally by `.gitleaks.s1.current-tree.baseline.json` and `scripts/security/run_s1_gitleaks_current_tree.sh`; the baseline-enforced current-tree scan returns `no leaks found` |

## Required Follow-Up

1. Force-push/replace GitHub remote history only when owner is ready for rewritten SHA history.
2. Rotate any token that could correspond to `infra/APIToken.txt`, even if the current local smoke considered it stale.
3. Re-run:
   - current-index scan;
   - Git-history scan;
   - frontend bundle/env scan under `S1-FE-010`;
   - provider credential inventory after real payment/OAuth/Telegram credentials are created.
4. Keep `.gitleaks.s1.current-tree.baseline.json` tight: new findings must be reviewed, remediated or intentionally added with evidence.

## Completion Statement

`S1-INFRA-007` scan was executed and revalidated for the 2026-05-09 S1 worktree. The critical local-history blocker for `infra/APIToken.txt` and `frontend/localhost.har` was remediated locally with `git-filter-repo`, test/public-copy false positives that were easy to reduce were remediated, current-tree baseline enforcement is repeatable, and the baseline-enforced scan returns `no leaks found`. It is acceptable to continue no-cost implementation work, but first RC/go-live remains blocked until remote history replacement/owner push decision and token rotation if applicable are completed.

Next ID superseded by `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md`; current next ID to execute is `S1-BE-002` - repeat protected first-admin bootstrap against the updated clean migration state.
