# Mini App Launch Control Runbook

## Scope

This runbook covers operator-owned Mini App launch-control incidents and rollout decisions across:

- rollout mode changes
- live promotion readiness
- rollback activation
- maintenance hold state
- launch blockers and ownership drift

Primary dashboard:

- Grafana: `/d/cybervpn-miniapp-runtime/cybervpn-miniapp-runtime`

Primary admin surface:

- Admin governance policy console: Mini App runtime, launch readiness, and launch actions

## Primary Signals

Prometheus metrics:

- `miniapp_launch_state_current`
- `miniapp_runtime_rollout_mode_current`
- `miniapp_launch_live_switch_allowed`
- `miniapp_launch_blockers_current`
- `miniapp_launch_actions_total`

Alert rules:

- `MiniAppLaunchBlockedWhileLive`
- `MiniAppRollbackModeActiveTooLong`
- `MiniAppReadyForLiveStalled`

## Triage Order

1. Confirm current `launch_state`, `runtime mode`, and `live_switch_allowed`.
2. Check whether the current state came from an intentional operator action or drift after readiness changes.
3. Review current blockers and the missing owner fields:
   - incident channel
   - rollback commander
   - primary on-call
4. Verify whether checkout canary and config canary are still green in the runtime dashboard.
5. Only after state and blockers are understood, decide whether to:
   - keep canary
   - promote live
   - enter maintenance
   - start rollback

## Launch Blocked While Live

Symptoms:

- `MiniAppLaunchBlockedWhileLive` fires
- runtime is still `live`
- launch blockers are present

Checks:

- inspect `miniapp_launch_state_current{launch_state="blocked"}`
- inspect `miniapp_runtime_rollout_mode_current{mode="live"}`
- inspect `miniapp_launch_blockers_current`
- open the admin policy console and read the server-derived launch summary

Likely causes:

- readiness gates were edited after live promotion
- incident ownership fields were cleared
- canary validation flags were reverted

Immediate mitigation:

- if active customer impact exists, execute `start_rollback`
- if runtime is healthy but evidence or staffing is missing, execute `enter_maintenance`
- do not keep `live` while the summary is blocked without an explicit incident commander decision

## Rollback Mode Active Too Long

Symptoms:

- `MiniAppRollbackModeActiveTooLong` fires
- runtime remains in rollback well past the expected containment window

Checks:

- confirm whether rollback is still actively mitigating user harm
- check whether a return-to-canary path is already available in launch summary
- verify on-call, rollback commander, and customer comms are still staffed

Likely causes:

- rollback started but exit decision was never completed
- canary follow-up validation did not happen
- incident ownership is unclear

Immediate mitigation:

- if the incident is still active, keep rollback and update the incident thread
- if rollback containment is complete, use `return_to_canary`
- if canary is not safe, use `enter_maintenance` and keep customer messaging current

## Ready For Live Stalled

Symptoms:

- `MiniAppReadyForLiveStalled` fires
- runtime is in canary and all launch gates are green for an extended period

Checks:

- confirm customer impact is absent
- verify checkout and config canary panels are healthy
- verify support window and release window note are still current

Likely causes:

- promotion decision was deferred and never resumed
- operator handoff drift
- release window expired

Immediate mitigation:

- either execute `promote_to_live`
- or update readiness / release window notes and keep canary intentionally
- do not ignore this alert if the launch was expected to move forward

## Action Discipline

Use launch actions only through the admin control plane so audit and metrics stay authoritative.

Preferred actions:

- `promote_to_live` only when `launch_state=ready_for_live`
- `start_rollback` when live or canary user impact is active
- `enter_maintenance` when ownership or readiness is incomplete and public exposure must pause
- `return_to_canary` after rollback containment when a safe limited cohort still exists

## Exit Criteria

The launch-control incident can be closed when:

- alert has cleared
- current launch summary matches the intended rollout state
- ownership fields are present
- blockers count is zero, or the remaining state is intentionally `maintenance`
- the chosen action is recorded in audit and the incident thread
