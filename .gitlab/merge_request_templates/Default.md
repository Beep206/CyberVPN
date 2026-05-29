# Summary

Briefly state what changed and why.

# Scope Classification

Choose exactly one:

- [ ] Green - docs, tests, non-sensitive copy, or isolated UI only.
- [ ] Amber - support, admin, partner, TMA, user-generated content, user data, notifications, or worker behavior.
- [ ] Red - payments, auth core, admin permissions core, production secrets, production deploy, VPN provisioning, Remnawave production config, or infrastructure exposure.

Risk label to apply: `risk::green`, `risk::amber`, or `risk::red`.

# Touched Paths

List the main paths changed.

```text
-
```

# What Was Intentionally Not Changed

List nearby scope that was deliberately left alone.

```text
-
```

# Tests Run

List local checks and exact commands. Use `not run` with a reason when a check is not applicable.

```text
-
```

# Remote CI

- Pipeline URL:
- Pipeline status:
- Failed jobs, if any:

# Screenshots / UI Evidence

Required for UI, TMA, admin, partner, and user-visible changes.

```text
not applicable - explain why
```

# Security Notes

Cover auth, permissions, data isolation, secrets, rate limits, logging, and user-generated content when relevant.

```text
-
```

# Rollback Notes

Describe how to revert safely, including migrations or config changes if present.

```text
-
```

# Reviewer Agents Required

Check all required Paperclip gates:

- [ ] SecurityEngineer
- [ ] Quill QA
- [ ] Scribe Release Docs & Evidence Manager
- [ ] Orion CTO
- [ ] Lyra Product Designer
- [ ] Atlas Platform & Remnawave NodeOps Engineer
- [ ] Ledger Billing & Subscription Risk Analyst
- [ ] Human owner / Board
- [ ] None beyond CI for Green scope

# Paperclip Links

- Parent issue:
- Child issue:
- Evidence document:

# Labels

Apply the relevant labels before merge:

```text
lane::autonomous
risk::green | risk::amber | risk::red
area::backend | area::frontend | area::admin | area::partner | area::telegram | area::docs
data::none | data::synthetic-only | data::sensitive
needs::security | needs::qa | needs::luma
sentinel::candidate
```

# Merge Gate

- [ ] Branch starts with `ai/`.
- [ ] CI pipeline is green.
- [ ] All GitLab discussions are resolved.
- [ ] Required Paperclip reviewer gates are complete.
- [ ] Source branch can be deleted after merge.
