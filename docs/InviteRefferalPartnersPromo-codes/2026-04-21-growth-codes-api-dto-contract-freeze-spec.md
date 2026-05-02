# Growth Codes API DTO Contract Freeze Spec

**Date:** 2026-04-21  
**Status:** contract baseline

---

## 1. Public Client APIs

Recommended endpoints:

- `GET /api/v1/rewards/overview`
- `GET /api/v1/invites/my`
- `POST /api/v1/invites/redeem`
- `GET /api/v1/invites/redemptions`
- `GET /api/v1/referral/status`
- `GET /api/v1/referral/code`
- `GET /api/v1/referral/stats`
- `GET /api/v1/referral/rewards`
- `POST /api/v1/codes/resolve`
- `POST /api/v1/codes/redeem`
- `GET /api/v1/codes/my-activity`
- `POST /api/v1/gifts/purchase/quote`
- `POST /api/v1/gifts/purchase/commit`
- `GET /api/v1/gifts/my`
- `POST /api/v1/gifts/redeem`
- `GET /api/v1/gifts/redemptions`

---

## 2. Checkout Contract

Quote requests should accept:

- plan selection
- duration
- add-ons
- code input
- wallet amount
- channel

Quote responses should return:

- price breakdown
- accepted or rejected code result
- conflicts
- entitlements snapshot
- reservation or redemption context where applicable

Code resolution payload should support machine-readable fields such as:

- `issuer_type`
- `owner_type`
- `code_type`
- `action_context`
- `result`
- `reject_reason`
- `conflicts`

Legacy `promo validate` style endpoints may still exist during migration, but they are not the source of truth for final checkout application.

Canonical flow:

- quote
- reservation where required
- commit
- consume or release reservation

---

## 2.1 Core Client DTOs

### `CodeResolutionResult`

```ts
type CodeResolutionResult = {
  accepted: boolean;
  code_type: 'invite' | 'referral' | 'promo' | 'gift' | 'partner' | null;
  action_context: 'checkout' | 'redeem' | 'signup' | 'admin_lookup';
  result: 'accepted' | 'rejected' | 'conflicted' | 'blocked_by_risk';
  reject_reason?: string;
  conflict_code?: string;
  policy_version_id?: string;
  reservation_id?: string;
  wrong_context_target?: 'checkout' | 'redeem';
  user_message_key: string;
}
```

### `GrowthCodeSummary`

```ts
type GrowthCodeSummary = {
  id: string;
  masked_code: string;
  code_type: 'invite' | 'referral' | 'promo' | 'gift';
  status: string;
  issuer_type: string;
  owner_type: string;
  starts_at?: string;
  expires_at?: string;
  uses_count: number;
  max_uses?: number;
}
```

### `InviteCodeView`

```ts
type InviteCodeView = {
  id: string;
  masked_code: string;
  friend_days: number;
  expires_at: string;
  status: 'active' | 'used' | 'expired' | 'revoked';
  source_type: string;
  used_at?: string;
  used_by_masked?: string;
}
```

### `ReferralStatsView`

```ts
type ReferralStatsView = {
  referral_code: string;
  referral_link: string;
  clicks: number;
  signups: number;
  qualifying_orders: number;
  pending_rewards_usd: string;
  available_rewards_usd: string;
  reversed_rewards_usd: string;
  monthly_cap_used_usd: string;
  lifetime_cap_used_usd: string;
}
```

### `GiftCodeView`

```ts
type GiftCodeView = {
  id: string;
  masked_code: string;
  plan_family: 'basic' | 'plus' | 'pro' | 'max';
  duration_days: 30 | 90 | 180 | 365;
  status: 'created' | 'sent' | 'redeemed' | 'expired' | 'revoked';
  recipient_hint?: string;
  redeemed_at?: string;
}
```

### `CheckoutQuoteResponse`

```ts
type CheckoutQuoteResponse = {
  base_amount: string;
  addons_amount: string;
  discounts: Array<{
    type: 'promo' | 'referral';
    code: string;
    amount: string;
    policy_version_id: string;
  }>;
  wallet_applied: string;
  gateway_amount: string;
  code_resolution: CodeResolutionResult;
  entitlements_snapshot: Record<string, unknown>;
}
```

### `AdminGrowthCodeDetail`

```ts
type AdminGrowthCodeDetail = {
  summary: GrowthCodeSummary;
  issuance: {
    issuance_type: string;
    source_order_id?: string;
    source_plan_sku?: string;
    issued_by_admin_id?: string;
    reason_code?: string;
  };
  counters: {
    touchpoints: number;
    signups: number;
    redemptions: number;
    rewards: number;
  };
  latest_risk_status?: string;
}
```

---

## 3. Admin APIs

Recommended endpoints:

- `GET /api/v1/admin/growth-codes`
- `POST /api/v1/admin/growth-codes`
- `GET /api/v1/admin/growth-codes/{id}`
- `PUT /api/v1/admin/growth-codes/{id}`
- `POST /api/v1/admin/growth-codes/{id}/pause`
- `POST /api/v1/admin/growth-codes/{id}/revoke`
- `POST /api/v1/admin/growth-codes/{id}/extend-expiry`
- `GET /api/v1/admin/growth-codes/{id}/touchpoints`
- `GET /api/v1/admin/growth-codes/{id}/signups`
- `GET /api/v1/admin/growth-codes/{id}/redemptions`
- `GET /api/v1/admin/growth-codes/{id}/rewards`
- `GET /api/v1/admin/growth-codes/{id}/audit`
- `GET /api/v1/admin/promo-campaigns`
- `POST /api/v1/admin/promo-campaigns`
- `GET /api/v1/admin/gift-batches`
- `POST /api/v1/admin/gift-batches`
- `POST /api/v1/admin/gift-batches/{id}/issue`
- `POST /api/v1/admin/invites/grants`
- `POST /api/v1/admin/growth-rewards/{id}/reverse`
- `GET /api/v1/admin/code-lookup`
- `GET /api/v1/admin/code-redemptions`
- `GET /api/v1/admin/growth-rewards`
- `GET /api/v1/admin/referral-abuse-reviews`

---

## 4. Partner-Touchpoint APIs

Only limited endpoints:

- `GET /api/v1/partner-campaign-assets`
- `GET /api/v1/partner-approved-promotions`
- `GET /api/v1/partner/reseller-voucher-batches`
- `POST /api/v1/partner/reseller-voucher-batches/request`
- `GET /api/v1/partner/reseller-voucher-redemptions`

---

## 5. Core Errors

Required error set:

- `CODE_NOT_FOUND`
- `CODE_EXPIRED`
- `CODE_NOT_ACTIVE`
- `CODE_EXHAUSTED`
- `CODE_ALREADY_REDEEMED`
- `CODE_NOT_ELIGIBLE_FOR_SKU`
- `CODE_NOT_ELIGIBLE_FOR_SURFACE`
- `CODE_CONFLICTS_WITH_PARTNER_CODE`
- `CODE_CONFLICTS_WITH_PARTNER_BINDING`
- `CODE_CONFLICTS_WITH_PROMO`
- `CODE_WRONG_CONTEXT`
- `CODE_REQUIRES_AUTH`
- `CODE_BLOCKED_BY_RISK`
- `GIFT_ALREADY_REDEEMED`
- `INVITE_SELF_REDEMPTION_BLOCKED`

---

## 6. Idempotency

Required on:

- invite redeem
- gift redeem
- gift purchase commit
- quote commit
- reward allocation
- admin revoke and pause actions
- admin manual grants
- admin reward reversals

---

## 7. Permission Model

Client endpoints:

- customer-authenticated except anonymous-safe resolve endpoints if desired

Admin endpoints:

- growth or support roles only

Partner endpoints:

- partner role plus explicit capability

---

## 8. DTO Principles

- no frontend-derived totals as source of truth
- no raw gift or invite value in logs or analytics DTOs
- include machine-readable conflict reasons
- include human-display messages only as optional presentation layer
- include enough context for admin lookup and support diagnosis without exposing raw secrets
- preserve policy version and reservation references across quote and commit
- model partner binding conflicts explicitly, not only partner code conflicts

---

## 9. Tracking And Audit Fields

Critical DTOs should be able to carry or reference:

- `issuer_type`
- `owner_user_id` or owner reference
- `source_order_id`
- `touchpoint_id`
- `signup_attribution_id`
- `reservation_id`
- `redemption_id`
- `reward_allocation_id`
- `risk_decision_id`
- `admin_actor_id` where relevant
