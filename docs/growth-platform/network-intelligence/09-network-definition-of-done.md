# Network Definition of Done

## Product DoD

- public network pages show real, sanitized network intelligence rather than decorative live-like placeholders;
- users can move from proof pages into conversion surfaces cleanly.

## Technical DoD

- public API reads from sanitized snapshots;
- direct public Prometheus access is eliminated;
- freshness and stale handling are explicit;
- snapshot publication is atomic and preserves last valid snapshot.

## Public Truth DoD

- no mock live data is shown as truth;
- incidents and uptime windows are operationally grounded;
- confidence and methodology are visible where needed.

## SEO DoD

- public pages support structured metadata, canonical rules, and meaningful content;
- region pages launch only where signal quality supports them.

## Widget DoD

- partner widgets use snapshot-derived data;
- rate limits and customization rules are enforced.

## Observability DoD

- snapshot freshness alerts exist;
- public API error and cache metrics exist;
- degraded mode is testable and visible.
