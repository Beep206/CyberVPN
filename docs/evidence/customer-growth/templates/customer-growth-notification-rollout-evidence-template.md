# Customer Growth Notification Rollout Evidence Template

**Use for:** staging or pre-production rollout windows validating repaired customer growth notification delivery flows.

---

## Metadata

- **Run ID:** `<run-id>`
- **Date:** `<YYYY-MM-DD>`
- **Environment:** `<staging|production-canary|production>`
- **Release Ring:** `<ring>`
- **Owner:** `<owner>`
- **Participants:** `<participants>`
- **CI Workflow URL:** `<workflow-url>`
- **Result:** `pending`

---

## Preconditions

- [ ] customer growth notification conformance workflow green
- [ ] committed OpenAPI spec in sync
- [ ] committed frontend generated API types in sync
- [ ] committed admin generated API types in sync
- [ ] dashboard `customer-growth-notification-delivery` available
- [ ] alert rules for unresolved backlog and recovery ratio loaded
- [ ] rollback owner online
- [ ] evidence directory created

---

## Scenario Matrix

| Scenario ID | Description | Status | Evidence Link | Notes |
|---|---|---|---|---|
| GCN-REPAIR-001 | `preferences_reenabled` auto-recovers an email delivery | pending | `./api/gcn-repair-001/` | |
| GCN-REPAIR-002 | `contact_data_corrected` re-arms blocked email delivery | pending | `./api/gcn-repair-002/` | |
| GCN-REPAIR-003 | `telegram_linked` re-arms blocked Telegram delivery | pending | `./api/gcn-repair-003/` | |
| GCN-REPAIR-004 | `support_resolved` closes escalation and emits closure notice | pending | `./api/gcn-repair-004/` | |

---

## CI Gate Evidence

| Check | Result | Evidence Link |
|---|---|---|
| backend conformance pack | pending | `./logs/backend-conformance.txt` |
| frontend surface readiness | pending | `./logs/frontend-conformance.txt` |
| admin surface readiness | pending | `./logs/admin-conformance.txt` |
| rollout asset validation | pending | `./logs/assets-conformance.txt` |

---

## Dashboard And Alert Proof

| Signal | Result | Evidence Link | Notes |
|---|---|---|---|
| unresolved backlog delta visible | pending | `./screenshots/unresolved-backlog.png` | |
| recovery ratio visible | pending | `./screenshots/recovery-ratio.png` | |
| `CustomerGrowthNotificationUnresolvedBacklogHigh` rule loaded | pending | `./exports/alert-rule-unresolved.json` | |
| `CustomerGrowthNotificationRecoveryRatioLow` rule loaded | pending | `./exports/alert-rule-recovery-ratio.json` | |

---

## Recovered vs Unresolved Register

| Reference | Channel | Outcome | Evidence Link | Notes |
|---|---|---|---|---|
| `<reference>` | `<email|telegram|in_app>` | `recovered` | `./exports/<reference>-detail.json` | |
| `<reference>` | `<email|telegram|in_app>` | `unresolved` | `./exports/<reference>-detail.json` | |
| `<reference>` | `<email|telegram|in_app>` | `support_resolved` | `./exports/<reference>-detail.json` | |

---

## Divergence Register

| ID | Category | Description | Severity | Owner | Blocking | Disposition |
|---|---|---|---|---|---|---|

---

## Final Decision

- **Decision:** `pending`
- **Decision Owner:** `pending`
- **Timestamp:** `pending`
- **Summary:** `pending`
