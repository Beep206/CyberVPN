# CyberVPN Partner Platform Pilot Cohort Roster And Rollout Calendar

**Date:** 2026-04-17  
**Status:** Pilot cohort and rollout calendar package  
**Purpose:** define the cohort model, roster template, pilot sequencing, and rollout calendar for controlled partner-platform activation across the five lanes.

---

## 1. Document Role

This document exists to operationalize `R3` pilot activation and the controlled path into `R4`.

It should be used together with:

- [2026-04-17-partner-platform-operational-readiness-package.md](2026-04-17-partner-platform-operational-readiness-package.md)
- [2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md](2026-04-17-partner-platform-rehearsal-logs-and-evidence-archive-template.md)
- [2026-04-17-partner-platform-environment-specific-cutover-runbooks.md](2026-04-17-partner-platform-environment-specific-cutover-runbooks.md)

---

## 2. Cohort Design Principles

Pilot cohorts must follow these rules:

1. start with trusted participants, not random scale;
2. group cohorts by lane and by surface;
3. do not mix too many risk profiles in one cohort;
4. require named owners for support, finance, risk, and product;
5. define entry and exit criteria before inviting users or partners;
6. cap blast radius by account count, order volume, payout exposure, and geographic spread;
7. do not widen a cohort while unresolved blocking issues remain.

---

## 3. Cohort Types

| Cohort type | Purpose | Typical members | Suitable lanes |
|---|---|---|---|
| `internal` | staff-only validation under real-ish flows | employees, support, finance, QA | all lanes except live performance traffic |
| `friendly-customer` | low-risk controlled customer exposure | invited testers, community members | invite, referral |
| `trusted-creator` | validate creator economics and portal flows | handpicked creators or media partners | creator / affiliate |
| `trusted-reseller` | validate alternate pricebooks and storefront isolation | approved reseller or distribution partners | reseller / API / distribution |
| `restricted-performance` | validate approval-only media buyer lane | one or two tightly reviewed traffic partners | performance / media buyer |

---

## 4. Cohort Exclusion Rules

Do not include in early pilots:

- high-refund or previously abusive accounts;
- unknown payout recipients;
- partners without completed agreement or tax profile;
- performance traffic without declaration and creative approval;
- customers requiring high-touch enterprise obligations;
- large public communities before support runbooks are proven.

---

## 5. Cohort Roster Template

Use this roster structure for every pilot cohort.

```md
# Pilot Cohort Roster

**Cohort ID:** <cohort-id>
**Lane:** <invite|referral|creator|performance|reseller>
**Surface:** <official-web|partner-storefront|partner-portal|api|telegram|mobile|desktop>
**Environment Path:** <staging-only|staging-to-production>
**Release Ring:** <R3 or staged R3->R4>
**Primary Owner:** <owner>
**Finance Owner:** <owner or n/a>
**Risk Owner:** <owner or n/a>
**Support Owner:** <owner>
**Product Owner:** <owner>

| Participant ID | Type | Region | Surface | Payout Enabled | Support Tier | Blast-Radius Cap | Status |
|---|---|---|---|---|---|---|---|
| <id> | internal | <geo> | official-web | no | internal | 20 orders | planned |
```

---

## 6. Recommended Baseline Cohort Sizes

These are recommended starting limits, not fixed business commitments.

| Lane | First cohort size | Expansion condition |
|---|---|---|
| Invite / Gift | 25-100 internal or friendly users | no reward duplication, clean entitlement behavior |
| Consumer Referral Credits | 25-75 users | clean cap behavior and low abuse signals |
| Creator / Affiliate | 3-5 trusted creators | clean attribution, statement, and payout visibility |
| Performance / Media Buyer | 1-2 approved partners | clean declaration, probation, and reserve behavior |
| Reseller / API / Distribution | 1-3 trusted resellers | clean storefront isolation and settlement logic |

If any cohort needs more scale before evidence is clean, the platform is moving too fast.

---

## 7. Rollout Calendar Model

Use a relative calendar anchored to:

```text
T0 = pilot-go-live approval for the specific lane or surface
```

## 7.1 Relative Calendar

| Window | Objective | Typical outputs |
|---|---|---|
| `T-4 to T-2 weeks` | finalize cohort, staff coverage, and runbooks | approved roster, support coverage, rollback owner assignment |
| `T-2 to T-1 weeks` | run staging rehearsals and shadow comparisons | rehearsal evidence, clean blocker register |
| `T-5 to T-1 days` | final production-readiness review | go/no-go package, exact cutover window |
| `T0` | activate pilot cohort | cutover evidence and initial smoke |
| `T+1 day` | first operational review | error budget, support load, early divergences |
| `T+3 days` | finance/risk/support checkpoint | pilot hold/widen decision |
| `T+7 days` | pilot phase review | widen, continue, or contain |
| `T+14 days` | late pilot review | recommend `R4` or extended pilot |

---

## 8. Lane-Specific Rollout Calendar Guidance

## 8.1 Invite / Gift

Recommended path:

1. internal cohort on official web;
2. friendly-customer cohort on official web;
3. optional channel expansion once entitlement parity is clean.

## 8.2 Consumer Referral Credits

Recommended path:

1. internal cohort with synthetic friend flows;
2. friendly-customer cohort with strict cap monitoring;
3. wider official-web rollout only after abuse thresholds stay clean.

## 8.3 Creator / Affiliate

Recommended path:

1. internal portal-only validation;
2. trusted creator cohort with statements visible but tight hold controls;
3. expanded approved-creator cohort once finance and support sign off.

## 8.4 Performance / Media Buyer

Recommended path:

1. internal probation simulation only;
2. one restricted approved partner;
3. second approved partner only after first partner evidence is clean.

## 8.5 Reseller / API / Distribution

Recommended path:

1. internal staging storefront rehearsal;
2. one trusted reseller on controlled host;
3. second or third reseller only after support routing and settlement remain stable.

---

## 9. Cohort Success Metrics

Each cohort must define:

- activation count;
- qualifying order count;
- refund rate;
- dispute rate;
- D7 or D30 retention marker where relevant;
- support ticket rate;
- attribution divergence;
- payout liability stability if applicable;
- entitlement error count where service access is involved.

Recommended template:

```md
## Cohort Success Metrics

| Metric | Threshold | Result | Status |
|---|---|---|---|
| refund rate | < 10% | 4.1% | pass |
| dispute rate | < 1% | 0% | pass |
| support ticket rate | <= defined baseline | 1.2x baseline | hold |
```

---

## 10. Promotion And Containment Rules

Pilot widening requires:

- no unresolved severity-high blockers;
- rollback path still available;
- support staffing confirmed for the next cohort;
- finance sign-off for any payout-bearing lane;
- risk sign-off for any traffic-bearing lane;
- evidence archive updated for the prior cohort.

Containment triggers:

- refund or dispute behavior above threshold;
- unexplained attribution divergence;
- legal acceptance evidence gap;
- payout visibility mismatch;
- wrong pricing or markup on official surfaces;
- entitlement drift affecting service access.

---

## 11. Rollout Calendar Template

```md
# Rollout Calendar

| Date / Window | Lane | Cohort ID | Surface | Release Ring | Owner | Decision Gate |
|---|---|---|---|---|---|---|
| <date> | creator | cohort-creator-01 | partner-portal | R3 | partner ops | go/no-go board |
| <date> | reseller | cohort-reseller-01 | partner-storefront | R3 | product | support + finance sign-off |
```

---

## 12. Support And Communication Coverage

Every pilot cohort must define:

- support owner and backup;
- partner-ops owner if partner-facing;
- finance owner if payout-bearing;
- risk owner if abuse-sensitive;
- communication plan for pilot participants;
- escalation path for rollback or containment.

No pilot cohort should start without named support coverage.

---

## 13. Exit Criteria For This Roster And Calendar Package

This package is complete when:

- each lane has a controlled first-cohort model;
- roster fields are explicit enough to assign blast-radius caps and owners;
- the calendar is relative and repeatable across lanes;
- widening and containment rules are defined before any pilot starts.
