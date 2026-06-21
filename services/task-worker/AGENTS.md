# CyberVPN Task Worker Engineering Rules

Apply the root contract and `services/AGENTS.md`. This file is authoritative for
`services/task-worker/`.

Use `pyproject.toml`, current TaskIQ configuration, task registry, tests, and CI
workflow as the version and command source of truth. Python 3.13 is required.

## TaskIQ and durable task behavior

- Keep task names, queues, payload schemas, labels, and routing compatible.
- Register tasks through the established broker/task modules. Do not create
  hidden import-order registration or duplicate task names.
- Treat delivery as at-least-once. Every state-changing task needs a stable
  idempotency key and database/provider duplicate behavior.
- Acknowledge only after intended durable state is committed or safely handed
  off.
- Use bounded retries with backoff/jitter. Validation, authorization, malformed
  payload, and permanent provider failures are terminal.
- Preserve retry attempt, correlation/task ID, and terminal reason in safe
  diagnostics.
- Test duplicate delivery, crash/restart boundaries, timeout, cancellation,
  provider partial success, and dead-letter/terminal behavior.
- Do not use arbitrary sleeps, unbounded polling, unbounded concurrency, or
  unbounded batch/message sizes.
- Graceful shutdown must stop intake, finish/cancel according to policy, release
  resources, and close clients.

The established TaskIQ message shape and task names are compatibility
boundaries. Do not rely on deprecated `.with_labels()` behavior; set labels in
the task declaration/configuration pattern used by the service.

## Database, provider, and notification boundaries

- Keep transaction and outbox/event ordering explicit.
- Enforce idempotency/concurrency with durable constraints, not only an
  in-memory check.
- Reuse long-lived database, Redis, broker, and HTTP clients with explicit
  timeouts and limits.
- Preserve provider idempotency keys and classify failures before retry.
- Never log full task kwargs, email bodies containing sensitive data, provider
  payload secrets, tokens, cookies, payment data, VPN/subscription URLs, or PII.
- Metrics/logs should include safe task name, task/correlation ID, attempt,
  latency, duplicate result, and terminal outcome.

## Email template single source of truth

All email HTML templates live in:

`src/services/email/templates.py`

Provider clients (`resend`, `brevo`, SMTP/Mailpit, and future adapters) call the
shared renderer. Never duplicate or fork HTML templates in a client.

For production email HTML:

- Use table layout: `<table role="presentation">`, `<tr>`, and `<td>`.
- Put textual content in `<td>`; do not use `<div>`, `<p>`, or heading tags for
  text/layout.
- Put spacing on `<td>` with `padding`; do not use `margin`.
- Use hex colors only. Pair CSS `background-color` with the `bgcolor` attribute
  where required for email-client compatibility.
- Add `border="0"`, `cellspacing="0"`, and `cellpadding="0"` to presentation
  tables according to the existing template pattern.
- Repeat a web-safe `font-family` on each text-bearing `<td>` and `<a>`.
- Use pixel `line-height` with `mso-line-height-rule: exactly` where the existing
  compatibility pattern requires it.
- Use HTML `width` and CSS `max-width` only on tables. The content container uses
  the established fixed-width plus responsive-width pattern.
- Preserve the MSO ghost table and VML button pattern used by the canonical
  templates.
- Do not use `rgba`, `hsla`, named colors, gradients, text shadows,
  `letter-spacing`, `word-break`, unsupported display/layout CSS, inline remote
  background images, or unreliable media-query-only layout.
- Use `word-wrap: break-word` for long safe URLs.
- Set explicit dimensions and meaningful alt behavior for images. Do not add
  tracking pixels unless explicitly approved.
- Escape all user/provider-derived text and validate every link scheme/host.
- Keep locale, expiration, code, URL, and development-banner inputs explicit.
- Do not include passwords, refresh tokens, session cookies, VPN configuration,
  provider secrets, or unnecessary PII in email.

When changing a template, test the shared renderer and every provider adapter.
Verify at least plain link/text correctness, HTML escaping, locale variants,
development-banner behavior, long values, and a representative Outlook-safe
structure. Do not manually “fix” one provider's copy.

## Testing

Add relevant:

- task registration and serialization contract tests;
- handler unit tests;
- duplicate/idempotency/concurrency tests;
- Redis/broker/database integration tests;
- provider adapter tests with `respx`/fakes;
- retry classification and terminal/dead-letter tests;
- graceful shutdown tests;
- shared email renderer tests across locales and provider adapters;
- HTML structural assertions for required/banned email patterns.

Assert durable state, emitted/acknowledged messages, and rendered output rather
than only mock calls.

## Required validation

Use a Python 3.13 virtual environment with `.[dev]`. From
`services/task-worker/`:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest
```

Coverage must satisfy the configured threshold. Run broker/database/provider
integration tests and an email rendering/delivery smoke when those paths
change. Rerun final gates after the last relevant modification.
