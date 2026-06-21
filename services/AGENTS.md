# CyberVPN Services Rules

Apply the root completion contract plus these service rules.

- Workers and consumers must be idempotent and safe under duplicate delivery,
  retry, crash and partial external failure.
- Use bounded retries with backoff/dead-letter behavior. Never retry permanent
  validation or authorization failures indefinitely.
- Make transaction/outbox/event ordering explicit for financial,
  provisioning, notification and attribution workflows.
- Structured logs and metrics must include safe correlation identifiers but no
  secrets or customer payloads.
- Preserve service-specific nested AGENTS rules, including the task-worker
  email-template single-source-of-truth requirements.
- Add unit tests plus broker/database/external-adapter integration tests for
  changed durable behavior.
