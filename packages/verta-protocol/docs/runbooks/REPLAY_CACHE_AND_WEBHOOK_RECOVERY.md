# Replay Cache And Webhook Recovery

## Trigger

Use this runbook when replay-sensitive or webhook-consistency behavior drifts from the maintained expectations, including:

- duplicate webhook delivery is accepted unexpectedly
- reconcile lag exceeds the maintained target
- replay-sensitive inconsistency is detected across bridge instances
- webhook hinting or lifecycle reconciliation no longer converges cleanly

## Safe State

- Preserve shared durable store contents.
- Prefer deterministic denial over ambiguous replay recovery.
- Do not wipe replay records or device state unless the runbook explicitly concludes the state is unrecoverable.

## Immediate Actions

1. Inspect the most recent lifecycle summary for replay-sensitive flags and webhook reconciliation facts.
2. Verify whether the problem is duplicate delivery handling, stale webhook sequencing, or store replication drift.
3. Confirm that every bridge instance points at the same shared-durable backend.
4. Force a clean lifecycle or supported-upstream verification pass before declaring the incident resolved.
5. If drift remains, isolate the affected deployment label and stop promotion or enablement changes until replay behavior is trustworthy again.

## Validation

- `bash scripts/operator-profile-disable-drill.sh`
- `bash scripts/remnawave-supported-upstream-deployment-reality-verify.sh`

## Recoverability

- Recoverable artifacts: shared durable replay cache, webhook delivery log, deployment-reality evidence, supported-upstream lifecycle evidence.
- Non-recoverable artifacts: duplicate side effects already accepted by external systems before replay rejection was restored.
- Rotation required: no.
- Re-registration required: no.

## Escalation

Escalate if either condition holds:

- duplicate webhook rejection no longer passes after the backend is confirmed healthy
- replay drift cannot be localized to a single deployment label or store boundary
