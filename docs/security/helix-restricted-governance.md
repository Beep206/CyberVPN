# Helix Restricted Governance

## Purpose

Some Helix internals are too sensitive for broad project documentation. This document defines how restricted transport knowledge is stored, reviewed, and disclosed.

## Restricted Material

Restricted material includes:

- wire-level resilience details;
- fingerprint-evasion or anti-blocking implementation specifics;
- sensitive bootstrap credential handling details;
- emergency operational playbooks that would weaken the transport if broadly exposed.

## Storage Rules

- Restricted material must live only in designated internal security locations approved by `sre`.
- General repository docs may reference the existence of restricted material but must not duplicate it.
- Public-facing docs must describe capability and support, not mechanism.

## Access Policy

- `sre`: full access
- `ops`: access only to operational content required for rollout, pause, and rollback
- `admin`: access only to product and release implications unless deeper access is explicitly approved

## Review Policy

- Any change to restricted material requires `sre` review.
- Any change that affects rollout or benchmark interpretation also requires `admin` notification.
- Any change with node-side operational impact requires `ops` notification.

## Incident Disclosure Rules

- Incident summaries for broad audiences must avoid reproducing restricted implementation details.
- Postmortems may describe control failures and impact but should redact transport-sensitive internals unless a limited audience is explicitly authorized.
