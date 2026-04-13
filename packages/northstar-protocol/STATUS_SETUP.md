# Northstar Setup Status

## What Was Created

- Root operating rules in `AGENTS.md`
- Repo-scoped Codex config in `.codex/config.toml`
- Nine focused custom agents in `.codex/agents/`
- Nine repo-scoped skills in `.agents/skills/`
- Development workflow docs under `docs/development/`
- Safe starter scripts under `scripts/`
- Reusable templates under `docs/templates/`
- Authoritative spec index in `docs/spec/INDEX.md`

## Repository Assumptions

- Northstar will be implemented in Rust on stable toolchains by default.
- Remnawave remains an external control plane and subscription layer; no fork path is allowed.
- The session core must remain transport-agnostic and transport personas must remain replaceable.
- Windows and PowerShell are the first-class local development path, with Bash mirrors where cheap and clean.

## Missing Authoritative Inputs

- None at setup time.

## Conflicts Or Oddities Found

- The repository is not currently initialized as a git repo, so branch and worktree guidance is documented but not yet executable.
- The authoritative `docs/spec/` set appeared during setup and is now fully present.
- No Rust workspace or production crates exist yet, so verification wrappers are intentionally conservative and fail clearly until bootstrap begins.

## Recommended Next Step

- Initialize git if that has not been done yet.
- Use `northstar-spec-ingestion` plus `protocol_architect` to turn the authoritative docs into the first implementation-phase checklist.
- Start workspace bootstrap only after the initial requirements matrix and ADR needs are clear.

## Implementation Status

This file records the setup milestone only.
The implementation launch has now begun; see `docs/implementation/IMPLEMENTATION_STATUS.md` for the live milestone status.
