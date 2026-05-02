# White-Label API Contracts

## Endpoint List

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/partner/workspace` | Current workspace view |
| PATCH | `/api/v1/partner/workspace` | Workspace updates |
| GET | `/api/v1/partner/brand` | Brand theme state |
| PATCH | `/api/v1/partner/brand` | Brand updates |
| GET | `/api/v1/partner/bots` | Bot list |
| POST | `/api/v1/partner/bots` | Create draft bot |
| GET | `/api/v1/partner/bots/:id` | Bot details |
| POST | `/api/v1/partner/bots/:id/provision` | Start provisioning |
| POST | `/api/v1/partner/bots/:id/suspend` | Suspend bot |
| POST | `/api/v1/partner/bots/:id/rotate-token` | Rotate credential |
| GET | `/api/v1/partner/analytics` | Partner analytics |
| GET | `/api/v1/partner/payouts` | Payout state |
| POST | `/api/v1/partner/payouts/request` | Request payout |

## Contract Requirements

- all endpoints are tenant-authenticated;
- all bot mutations require explicit workspace ownership or admin override;
- state-mutating endpoints should use idempotency where retries are expected.

## `GET /api/v1/partner/workspace`

Returns:

- workspace status
- review status
- linked brand theme
- linked commercial policy
- linked storefront
- next required actions

## `PATCH /api/v1/partner/brand`

Allows moderated updates to:

- display name
- logo asset
- color tokens
- support profile
- selected branded copy fields

Returns moderation state and validation issues.

## `POST /api/v1/partner/bots`

Creates draft bot record.

Request example:

```json
{
  "displayName": "Example VPN",
  "defaultLocale": "en-EN"
}
```

## `POST /api/v1/partner/bots/:id/provision`

Starts provisioning job.

Response example:

```json
{
  "jobId": "uuid",
  "state": "queued"
}
```

Error codes:

- `partner_workspace_not_ready`
- `partner_brand_not_approved`
- `partner_bot_invalid_state`

## `POST /api/v1/partner/bots/:id/rotate-token`

Supports:

- managed credential rotation;
- manual token replacement in fallback mode;
- validation result in response.

## `GET /api/v1/partner/analytics`

Returns:

- visits
- Mini App opens
- trials
- payments
- revenue
- conversion
- top geographies
- top offers

## `POST /api/v1/partner/payouts/request`

Request must validate:

- verified settlement account;
- available balance;
- hold state;
- risk restrictions.
