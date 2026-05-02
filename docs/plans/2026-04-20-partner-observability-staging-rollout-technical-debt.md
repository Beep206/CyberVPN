# Partner Observability Staging Rollout Technical Debt

**Date:** 2026-04-20  
**Status:** Open technical debt  
**Purpose:** record the staging-only observability work that cannot be closed from local code validation alone.

---

## 1. Role Of This Document

This note tracks the remaining observability rollout work for the partner platform that is blocked on live staging access.

It exists so these items are not treated as implicit follow-up or hidden in commentary. They are explicit operational residuals after the code-side observability package and local conformance layers were completed.

These items are not implementation gaps in backend, partner frontend, admin frontend, Prometheus rules, Grafana dashboards, or runbook coverage. They are live-environment validation gaps.

---

## 2. Open Technical Debt Items

| ID | Item | Why Still Open | Closure Evidence |
|---|---|---|---|
| `OBS-DEBT-01` | run live `staging:partner-observability:smoke` | requires real staging hosts, credentials, and observability endpoints | command transcript plus generated evidence directory |
| `OBS-DEBT-02` | confirm synthetic events reach `Prometheus`, `Grafana`, and `Alertmanager` in staging | cannot be proven from local code or static config alone | Prometheus query evidence, Grafana dashboard evidence, Alertmanager API evidence |
| `OBS-DEBT-03` | assemble staging evidence pack for observability | requires a real staging run window | archived evidence pack with timestamps and scenario references |
| `OBS-DEBT-04` | perform at least one live alert fire-drill | requires live delivery path and live routing verification | alert screenshot or API evidence plus receiver proof |
| `OBS-DEBT-05` | make final observability rollout-readiness decision | depends on successful staging validation and evidence review | explicit `pass / hold / rollback` decision record |

---

## 3. Blocking Nature

These residuals are:

- not blockers for local code closure;
- blockers for live observability rollout closure;
- blockers for claiming full production-proven observability readiness.

In other words:

- code and configuration are ready;
- live operational proof is still pending.

---

## 4. Preconditions For Closure

Before these residuals can be retired, the following must exist:

- staging `partner` host;
- staging `admin` host;
- reachable staging `Prometheus`;
- reachable staging `Grafana`;
- reachable staging `Alertmanager`;
- disposable staging accounts if the validation path needs authenticated runtime checks;
- evidence directory for the exact staging window.

---

## 5. Execution Order

Retire these residuals in this order:

1. run `npm run staging:partner-observability:smoke`;
2. confirm synthetic frontend runtime and web-vitals events appear in staging metrics and dashboard queries;
3. archive evidence;
4. run one controlled alert fire-drill;
5. record rollout-readiness decision.

---

## 6. Exit Condition

This technical debt note may be marked closed only when:

- the staging smoke passes end-to-end;
- the live observability path is proven across ingest, metrics, dashboards, and alert routing;
- the evidence pack is archived;
- the alert fire-drill is documented;
- the final rollout-readiness decision is recorded explicitly.

