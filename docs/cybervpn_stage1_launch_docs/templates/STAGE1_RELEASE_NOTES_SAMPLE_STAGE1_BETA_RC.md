# CyberVPN S1 Release Notes Sample: `stage1-beta-rc.N`

> This is a sample only. It is not a release approval and must not be used as a live release note without replacing placeholders with real evidence.

## 1. Release Identity

| Field | Value |
|---|---|
| Release type | `RC` |
| Release tag | `stage1-beta-rc.N` |
| Commit SHA | `<immutable commit SHA>` |
| Source branch | `release/stage1-controlled-public-beta` |
| Prepared by | `<release operator>` |
| Prepared at | `2026-05-05 HH:MM Asia/Yekaterinburg` |
| Go/no-go owner | `@Sasha_Beep` |
| Support/on-call primary | `@Sasha_Beep` |
| Support/on-call backup | `@Sasha_Beep` |

## 2. Release Summary

This RC candidate is intended to prove the S1 B2C beta path with controlled scope:

- public website and web cabinet are included only for S1 B2C flows;
- Telegram Bot and Mini App are included only after bot/webhook evidence;
- trial and one payment provider path may be enabled only after staging evidence;
- partner, payouts, native releases, Helix/Verta/Beep production and auto-prolongation remain disabled.

## 3. Backlog IDs Included

| ID | Included change | Evidence |
|---|---|---|
| `S1-REL-002` | Fresh dirty worktree and launch scope map before RC | `<fresh evidence required>` |
| `S1-BE-001` | Clean staging DB migration proof | `<staging evidence required>` |
| `S1-BE-002` | First admin bootstrap proof | `<staging evidence required>` |
| `S1-PAY-001` | First live payment provider chosen | `<provider readiness evidence required>` |
| `S1-VPN-004` | Trial provisioning through real staging Remnawave | `<staging evidence required>` |
| `S1-OBS-004` | Alert delivery to Telegram and backup email | `<alert evidence required>` |

## 4. Explicitly Disabled / Out of Scope

| Area | Required state for this RC |
|---|---|
| Partner portal / payouts | Disabled |
| Referral / promo / gift public flows | Disabled by default |
| Add-ons | Disabled by default |
| Mobile store release | Out of S1 |
| Desktop / Android TV / browser extension | Out of S1 |
| Helix / Verta / Beep production | Disabled |
| Auto-prolongation | Not promised; manual renewal only |

## 5. Go/No-Go Snapshot

| Gate | Status | Notes |
|---|---|---|
| Dirty worktree/scope map | Pending | Must be fresh for this RC |
| Secrets scan | Pending | Current-tree scan required |
| Staging DNS/TLS | Pending | `.net` primary and `.org` redirects required later for live |
| Payment provider evidence | Pending | At least one provider needed for paid beta |
| Remnawave staging evidence | Pending | Trial and paid provisioning proof required |
| Backup/restore | Local pass / managed pending | Local backup/restore proof exists; managed staging/prod backup/restore and production RPO/RTO required before go-live |
| Rollback dry-run | Pending | Component rollback proof required |
| Observability/alerts | Pending | Alert delivery required |
| Legal/support | Pending | Final owner/legal approval and mailbox proof required |

## 6. Rollback Notes

If this RC fails:

- disable public registration;
- disable payments globally or disable the affected provider;
- stop new provisioning while preserving paid state;
- keep support/admin visibility available;
- roll back frontend/backend/bot to previous immutable artifact where safe;
- write incident note and update known issues.

## 7. Approval

| Role | Approver | Decision |
|---|---|---|
| Owner / go-no-go | `@Sasha_Beep` | Pending |
| Support/on-call | `@Sasha_Beep` | Pending |
| Finance/ops | `@Sasha_Beep` | Pending |
| Technical release | `<name>` | Pending |
