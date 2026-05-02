# Network API Contracts

## Endpoint List

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/public/network/overview` | Global public summary |
| GET | `/api/v1/public/network/regions` | Region list |
| GET | `/api/v1/public/network/regions/:id` | Region detail |
| GET | `/api/v1/public/network/leaderboard` | Ranked public regions |
| GET | `/api/v1/public/network/uptime` | Public uptime windows |
| GET | `/api/v1/public/network/incidents` | Public incident list |
| GET | `/api/v1/public/network/widget` | Widget payload or embed contract |
| GET | `/api/v1/public/network/dpi-score` | DPI score summary |
| GET | `/api/v1/public/network/seo-summary` | SEO-oriented summarized content payload |

## Common Response Requirements

- `version`
- `schemaVersion`
- `methodologyVersion`
- `measurementWindow`
- `generatedAt`
- `expiresAt`
- `freshnessStatus`
- `confidence`

## Cache Headers

Recommended default:

```text
Cache-Control: public, max-age=60, stale-while-revalidate=300
ETag: "<value>"
Last-Modified: "<http-date>"
```

## `GET /api/v1/public/network/overview`

Returns:

- global status
- regional counts
- median performance aggregates
- freshness and last generated time

## `GET /api/v1/public/network/regions`

Returns a paginated or bounded list of public regions with:

- region name
- status
- latency
- speed
- uptime
- confidence

## `GET /api/v1/public/network/incidents`

Returns current and recent public incidents with safe summaries and affected regions.

## `GET /api/v1/public/network/widget`

Returns widget configuration or payload depending on widget type. Must support rate limiting and partner-aware branding only where allowed.

## `GET /api/v1/public/network/dpi-score`

Returns only if DPI score is enabled and sufficiently trustworthy:

- enabled flag
- last updated time
- country-level public scores
- confidence
- supported protocol summaries

## Error Handling

Common error codes:

- `public_snapshot_unavailable`
- `public_snapshot_stale`
- `public_region_not_found`
- `public_dpi_not_enabled`

## Security Rules

- all responses must be sanitized before publish;
- no direct Prometheus proxy behavior;
- widget endpoints must not leak partner-private data.
