# CFLOW-011 Owner Manual Smoke And Production UX Edge Cases

Date: 2026-05-29

## Scope

- Accept owner manual smoke as the human validation layer after CFLOW-010 authenticated baseline.
- Confirm production surfaces are still reachable.
- Confirm runtime services are healthy after the latest admin runtime deploy.
- Avoid code changes unless a concrete defect is reported.

## Owner Input

Owner reported that the manual production check was completed.

No new concrete blocker, console trace, API failure, screenshot issue, or UX defect was provided for this batch. Therefore CFLOW-011 is closed as an evidence-only stabilization checkpoint.

## Production Endpoint Probe

```text
200 0.910166 https://cyber-vpn.net/ru-RU
200 0.900378 https://my.cyber-vpn.net/ru-RU/login
200 0.744143 https://admin.cyber-vpn.net/ru-RU/login
200 0.915559 https://partner.cyber-vpn.net/ru-RU/login
200 0.572497 https://api.cyber-vpn.net/healthz
```

## Runtime Snapshot

```text
cybervpn-admin    cybervpn/cybervpn-admin:cflow-010-feea5c11-20260529T0530Z    running    healthy
cybervpn-backend  cybervpn/cybervpn-backend:stage1-ci-157-0a70ea19             running    healthy
cybervpn-frontend cybervpn/cybervpn-frontend:cflow-009-e9ac3365-20260529T0039Z running    healthy
cybervpn-partner  cybervpn/cybervpn-partner:stage1-ci-157-0a70ea19             running    healthy
CYBERVPN_IMAGE_TAG=cflow-010-feea5c11-20260529T0530Z
```

## Baseline Carried Forward

CFLOW-010 authenticated browser smoke passed after the final admin deploy:

- customer routes: no bad responses, request failures, or console errors;
- admin 2FA/dashboard/customers/detail routes: no bad responses, request failures, or console errors;
- temporary smoke customer cleanup returned `200`.

Reference:

- `docs/evidence/releases/cflow-010/cflow-010-authenticated-smoke-and-admin-polish.md`

## GitLab State

```text
pipeline:163 status:manual sha:518cae79
```

This is not treated as a runtime blocker for CFLOW-011 because the production deploy and smoke were already completed outside the manual pipeline gate.

## Decision

CFLOW-011 status: `closed`

No deploy was required for this batch.

## Follow-Up Rule

If owner manual smoke finds a specific remaining UX/API issue later, open the next batch with a concrete reproduction:

- affected surface: `public`, `my`, `admin`, `partner`, `miniapp`, `bot`;
- route/page;
- expected behavior;
- actual behavior;
- screenshot or console/API trace when available.
