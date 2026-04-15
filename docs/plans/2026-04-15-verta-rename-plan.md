# Verta Protocol Naming Finalization Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the protocol repo fully aligned on the canonical `Verta` identity across docs, scripts, artifacts, workflows, and release-facing verification.

**Architecture:** The repository now uses a single public protocol name, a single artifact root, and a single package path. Internal Rust `ns-*` crate and binary identifiers remain stable where they do not leak a legacy product name, while all operator-facing and release-facing surfaces stay `Verta`-first.

**Tech Stack:** Rust workspace, Cargo, Bash/PowerShell wrappers, GitHub Actions, Markdown/JSON docs, release/runbook artifacts, Remnawave bridge integration.

---

## 1. Canonical Naming Rules

- Public protocol name: `Verta`
- Canonical package path: `packages/verta-protocol`
- Canonical artifact root: `target/verta`
- Canonical workflow prefix: `verta-udp-*`
- Canonical release labels: `verta-*`
- Canonical import and metadata surfaces: `verta://*`, `verta_*`, `verta.*`

## 2. Guardrails

The naming finalization must not change protocol semantics or deployment posture:
- Remnawave remains external and non-fork.
- Bridge deployment topology stays unchanged unless separately approved.
- Session core remains transport-agnostic.
- No accidental bridge-domain widening.
- `0-RTT` remains disabled unless separately and normatively approved.
- Verification and release evidence remain fail-closed and attributable.

## 3. Scope

Included:
- docs, specs, runbooks, release notes, and implementation status surfaces
- Bash and PowerShell wrappers
- `ns-testkit` release-facing examples and summary defaults
- workflow names, artifact labels, and release commands
- repo references to the protocol package path and artifact root

Excluded unless separately approved:
- renaming `ns-*` crates or binaries
- changing bridge/runtime architecture
- changing transport semantics

## 4. Workstreams

### 4.1 Docs And Specs

- Keep all human-facing protocol references on `Verta`
- Keep spec cross-links and release truth surfaces aligned with `packages/verta-protocol`
- Keep runbooks and verification commands pointed at `target/verta`

### 4.2 Scripts And Evidence

- Keep wrapper defaults canonical on `VERTA_*` inputs and `target/verta` outputs
- Keep release and phase summaries attributable under the Verta artifact root
- Keep fail-closed missing-input behavior intact during the rename cleanup

### 4.3 Workflows And Release Surfaces

- Keep workflow files and display names on `verta-*`
- Keep release evidence chain, phase signoffs, and production-ready surfaces Verta-only
- Keep artifact naming and upload labels aligned with Verta summaries

### 4.4 Verification

- Run formatting, linting, targeted wrapper validation, and workspace tests after rename slices
- Re-run repo-wide grep for stale product names until the remaining set is zero

## 5. Verification Commands

Base verification:

```bash
cargo fmt --manifest-path /home/beep/projects/VPNBussiness/packages/verta-protocol/Cargo.toml --all
cargo clippy --manifest-path /home/beep/projects/VPNBussiness/packages/verta-protocol/Cargo.toml --workspace --all-targets --all-features -- -D warnings
cargo test --manifest-path /home/beep/projects/VPNBussiness/packages/verta-protocol/Cargo.toml --workspace
```

Repository naming verification:

```bash
python - <<'PY'
from pathlib import Path
import re

root = Path("/home/beep/projects/VPNBussiness")
pattern = re.compile(r"(?i)n" + "orthstar")
for path in root.rglob("*"):
    if any(part in {".git", "node_modules", "target"} for part in path.parts):
        continue
    if not path.is_file():
        continue
    try:
        text = path.read_text()
    except Exception:
        continue
    if pattern.search(text):
        print(path)
PY
```

Wrapper validation:

```bash
bash -n /home/beep/projects/VPNBussiness/packages/verta-protocol/scripts/verta-compat.sh
git diff --check -- /home/beep/projects/VPNBussiness/packages/verta-protocol /home/beep/projects/VPNBussiness/.github/workflows /home/beep/projects/VPNBussiness/docs/plans
```

## 6. Exit Criteria

The naming finalization is complete only when all of the following are true:
- repo-wide search for the retired protocol name is empty outside generated artifacts
- public docs and release docs are fully `Verta`
- maintained wrappers and examples default to `VERTA_*` and `target/verta`
- workflows, package references, and release labels use `Verta`
- verification remains green after the cleanup

## 7. Smallest Next Task

`Act as protocol_verification_engineer. Re-run the Verta naming verification sweep, remove any newly introduced stale protocol-name references, rerun cargo fmt/clippy/test for packages/verta-protocol, and report only the remaining non-generated naming blockers.`
