# CyberVPN Platform Foundation P2.3 Collector Convergence Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live convergence evidence pending  
**Packet:** `P2.3`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `backend-platform`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.3` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-monorepo-inventory.md](2026-04-21-platform-foundation-monorepo-inventory.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.3` exists to freeze the repo-side collector convergence contract for the program:

- `Alloy` is the only target collector for new Kubernetes and VM surfaces;
- `promtail` and standalone long-lived `otel-collector` assumptions are treated as tracked migration debt only;
- new drift toward deprecated or superseded collector patterns is rejected at the repository level before live rollout exists.

Implementation note:

- this packet is being executed as a pre-launch `repo/validation` slice because live infrastructure is not available in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live Alloy rollout and real retirement of the tracked legacy collector surfaces.

---

## 2. Current Baseline

Before this packet:

- `P1.7` froze Alloy as the collector for new external control-plane systems;
- `P2.2` froze Alloy as the only target collector baseline for workload-cluster platform services;
- the inventory already recorded:
  - `infra/docker-compose.yml` still carries `promtail` and standalone `otel-collector`;
  - `infra/prometheus/prometheus.yml` still scrapes the standalone local `otel-collector`;
  - `backend/src/config/settings.py` still defaults `otel_exporter_endpoint` to `http://otel-collector:4317`;
  - old docs and prompts still encode obsolete collector assumptions.

Observed strengths:

- the architecture and inventory already define the target state clearly;
- the repo already contains Alloy rollout helpers for:
  - external control-plane VMs
  - workload-cluster platform services
- the temporary exceptions register already tracks:
  - `EX-007` for `promtail`
  - `EX-008` for standalone `otel-collector`.

Observed implementation risks:

- without a repository-level auditor, new code or docs can quietly reintroduce `promtail` or standalone `otel-collector` assumptions;
- broad descriptive docs can keep advertising obsolete collector topology even after the architecture is frozen;
- later `P2` packets can inherit false observability assumptions unless `P2.3` creates a concrete validation boundary now.

---

## 3. Canonical Decisions For P2.3

`P2.3` fixes the following decisions:

1. `Alloy` is the only valid target collector for newly introduced platform systems.
2. `promtail` is tracked migration debt only and must not be introduced into new implementation packets, helpers, or runtime surfaces.
3. Standalone long-lived `otel-collector` processes are tracked migration debt only and must not be introduced into new implementation packets, helpers, or runtime surfaces.
4. Repo-side drift is checked by a dedicated collector-convergence auditor.
5. The auditor distinguishes between:
   - tracked legacy references
   - unexpected new drift
6. Broad descriptive docs may mention migration debt only when they clearly state that `Alloy-only` is the target state.

---

## 4. Scope

In scope for `P2.3`:

- add a canonical helper under [infra/scripts/collector_convergence.py](../../infra/scripts/collector_convergence.py);
- add unit coverage for the helper;
- render a repo-side report that classifies collector references into tracked legacy versus unexpected drift;
- add a validation mode that fails when new unexpected references appear;
- update operator docs so the helper is discoverable from `infra/README.md`;
- retire low-cost stale assumptions in clearly normative repo surfaces where safe in the current workspace.

Out of scope for the current repository slice executed in this workspace:

- live replacement of local `promtail` or `otel-collector` services;
- live Alloy rollout for local Compose or workload clusters;
- full cleanup of every historical planning document in the repo;
- final removal of `EX-007` and `EX-008`.

---

## 5. Official Constraints

The execution of `P2.3` follows current primary-source guidance:

- Promtail is deprecated and reached end-of-life on 2026-03-02;
- Grafana documents migration from Promtail to Alloy and provides conversion tooling;
- Alloy is the successor collector direction for log and OTLP ingestion in the Grafana stack.

Primary sources:

- Promtail deprecation and EOL notice: https://grafana.com/docs/loki/latest/send-data/promtail/installation/
- Loki release notes and Promtail deprecation: https://grafana.com/docs/loki/latest/release-notes/v3-6/
- Migrate from Promtail to Alloy: https://grafana.com/docs/alloy/latest/tasks/migrate/from-promtail/
- Promtail page redirecting users to migrate: https://grafana.com/docs/loki/latest/send-data/promtail/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.3`:

### 6.1 Helper And Tests

- [infra/scripts/collector_convergence.py](../../infra/scripts/collector_convergence.py)
- [infra/tests/test_collector_convergence.py](../../infra/tests/test_collector_convergence.py)

### 6.2 Existing Surfaces Updated During P2.3

- [infra/tests/test_control_plane_observability.py](../../infra/tests/test_control_plane_observability.py)
- [infra/README.md](../../infra/README.md)
- [docs/CYBERVPN_FULL_DESCRIPTION.md](../../docs/CYBERVPN_FULL_DESCRIPTION.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-3-collector-convergence/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-3-collector-convergence/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.3.1` Freeze The Repo-Side Collector Auditor

**Goal:** stop new collector drift from entering the monorepo unnoticed.

Deliverables:

- `collector_convergence.py`
- `render-report` command
- `validate` command
- tracked-legacy vs unexpected classification model

Acceptance criteria:

- helper renders machine-readable and human-readable reports;
- helper returns a non-zero exit code when unexpected references exist;
- tracked migration debt does not fail validation by itself.

### 7.2 `T2.3.2` Freeze The Tracked-Legacy Boundary

**Goal:** make current collector debt explicit instead of letting it stay as undocumented background noise.

Deliverables:

- tracked legacy glob set in the helper
- classification of:
  - canonical platform plans and evidence docs
  - current local-stack collector remnants
  - runtime defaults still waiting for migration

Acceptance criteria:

- known legacy references are visible in the generated report;
- unexpected references are separated cleanly from tracked migration debt.

### 7.3 `T2.3.3` Retire Low-Cost Stale Assumptions In Normative Surfaces

**Goal:** stop clearly normative repo surfaces from advertising obsolete collector topology where easy cleanup is safe now.

Deliverables:

- broad descriptive doc wording corrected toward Alloy-only target state
- stale test assertion corrected to validate policy rather than a specific deprecated component name

Acceptance criteria:

- the updated descriptive doc no longer presents `promtail` and standalone `otel-collector` as the canonical observability stack;
- tests still validate the intended policy successfully.

### 7.4 `T2.3.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any live collector cutover exists.

Deliverables:

- helper unit tests
- local report render
- local validation run
- packet evidence pack
- formal carry-forward residual for missing live convergence proof

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are explicit;
- later `P2` packets may begin without pretending collector convergence is already complete.

---

## 8. State-Boundary Rules

`P2.3` must keep the following invariants:

1. `Alloy` is the only target collector for new systems.
2. Repository validation must reject new unexpected `promtail` or standalone `otel-collector` references.
3. Tracked migration debt remains visible until it is actually removed; it must not be hidden by the helper.
4. A doc may mention legacy collector debt only when it clearly frames it as migration debt rather than target-state design.
5. `P2.3` must not pretend that live collector cutover is complete from repository-only work.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| new packets reintroduce `promtail` or standalone OTEL assumptions | collector convergence silently regresses | add repo-side validation that flags unexpected references |
| historical docs get treated as current architecture | operators and later packets follow the wrong topology | keep broad descriptive docs aligned and keep old planning references tracked as debt only |
| tracked debt gets hidden instead of managed | exceptions become invisible and harder to retire | helper reports tracked legacy references separately instead of suppressing them |
| `P2.3` is treated as full collector cutover | later packets assume live observability convergence already exists | carry forward `EX-023` until live rollout and real retirement proof exist |
