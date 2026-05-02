# CyberVPN Platform Foundation P2.3 Collector Convergence Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.3`  
**Phase:** `P2`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `backend-platform`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.3`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-3-collector-convergence-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-3-collector-convergence-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- this evidence pack currently carries `EX-023` as the formal reason `P2.3` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.3` result:

- canonical helper added at `infra/scripts/collector_convergence.py`;
- helper renders:
  - `collector-convergence-report.json`
  - `collector-convergence-report.md`
- helper validates that new unexpected `promtail` or standalone `otel-collector` drift is absent from the repository;
- low-cost stale assumptions were corrected in:
  - `docs/CYBERVPN_FULL_DESCRIPTION.md`
  - `infra/tests/test_control_plane_observability.py`
- operator docs updated so the helper is discoverable from `infra/README.md`.

This packet is **not yet claimed complete** because:

- local Compose still carries the tracked legacy `promtail` and standalone `otel-collector` services;
- `infra/prometheus/prometheus.yml` still carries the tracked legacy local `otel-collector` scrape job;
- `backend/src/config/settings.py` still carries the tracked legacy `otel_exporter_endpoint` default;
- no live Alloy cutover evidence exists yet for the remaining tracked legacy surfaces.

That is intentional. `P2.3` first closes the repo-side validation boundary and begins low-cost retirement work, while leaving actual live cutover proof explicit.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/collector_convergence.py`
  - scans the repository for:
    - `promtail`
    - `otel-collector`
    - `opentelemetry-collector`
  - classifies matches as:
    - `tracked_legacy`
    - `unexpected`
  - renders JSON and Markdown reports
  - fails validation if unexpected references exist

- `infra/tests/test_collector_convergence.py`
  - validates report rendering
  - validates tracked vs unexpected classification
  - validates pass/fail behavior of the helper

### 3.2 Low-Cost Stale-Assumption Cleanup

- `docs/CYBERVPN_FULL_DESCRIPTION.md`
  - no longer presents `promtail` and standalone `otel-collector` as the canonical observability stack
- `infra/tests/test_control_plane_observability.py`
  - now validates the intended collector policy rather than keying on a deprecated component name

### 3.3 Operator Docs And Program Records

- `infra/README.md`
  - now documents `collector_convergence.py` as the canonical `P2.3` helper
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-023`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_collector_convergence
```

Result:

- `Ran 3 tests`
- `OK`

### 4.2 Existing Related Test Still Passes

Command:

```bash
python -m unittest infra.tests.test_control_plane_observability
```

Result:

- `Ran 2 tests`
- `OK`

### 4.3 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/collector_convergence.py
```

Result:

- compilation completed successfully

### 4.4 Helper Report Render

Command shape:

```bash
python infra/scripts/collector_convergence.py render-report \
  --repo-root . \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against the current repository
- report artifacts were created:
  - `collector-convergence-report.json`
  - `collector-convergence-report.md`
- current repo summary at render time:
  - tracked legacy matches: `154`
  - unexpected matches: `0`

### 4.5 Helper Validation Run

Command:

```bash
python infra/scripts/collector_convergence.py validate --repo-root .
```

Result:

- validation passed with tracked legacy matches only
- current repo validation summary:
  - tracked legacy matches: `154`
  - unexpected matches: `0`
- no unexpected collector-drift matches were reported in the current repository workspace

### 4.6 Workspace Readiness Check For Live Convergence Evidence

Observed in the current workspace on 2026-04-22:

- no live Alloy replacement exists yet for local Compose `promtail` or standalone `otel-collector`;
- no live cutover evidence exists yet for the backend OTLP target default migration;
- no live workload-cluster or VM fleet evidence exists yet that the remaining tracked legacy surfaces have been retired.

Meaning:

- the packet cannot honestly claim repo-wide collector convergence is complete yet;
- `P2.3` must therefore carry a formal residual until the remaining tracked legacy collector surfaces are actually removed or replaced and proven in runtime evidence.

---

## 5. Remaining Live Closure Requirements

`P2.3` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. the remaining tracked legacy collector surfaces are either removed or formally superseded:
   - `infra/docker-compose.yml`
   - `infra/prometheus/prometheus.yml`
   - `backend/src/config/settings.py`
2. the helper report still returns zero unexpected collector-drift references after that cleanup;
3. live Alloy-based replacement evidence exists for the affected runtime surfaces where applicable;
4. `EX-007` and `EX-008` are either retired or explicitly narrowed to zero non-local scope.
