# Plan: Invite / Referral / Promo / Partner Codes + Wallet System

## Context

CyberVPN needs 4 code systems (invite, referral, promo, partner) plus a user wallet to support monetization, growth, and reseller channels. Currently the backend has no referral/promo/partner logic. The Flutter mobile app already has referral UI waiting for backend API. All systems can be combined simultaneously during a single payment. The wallet supports payments for VPN and crypto withdrawals.

## Business Model Summary

- **Invite codes**: Earned by buying subscriptions (admin configures plan → N invites × M free days). Friends register with code → free VPN.
- **Referral codes**: Permanent per-user link. Referrer earns configurable % from referred user's payments. Duration: indefinite / time-limited / payment-count / first-only.
- **Promo codes**: Admin-created discount codes (% or fixed). Single/multi-use, optional expiry, plan restrictions.
- **Partner codes**: Reseller model. Partner sets markup (up to 300%). Earns markup + tiered commission % of base price. Client permanently bound to partner.
- **Wallet**: USD balance. Funded from referral/partner earnings + admin top-ups. Spend on VPN or withdraw to crypto.

## Price Calculation Order (Checkout)

```
1. Base price (from subscription_plans.price_usd)
2. + Partner markup: base × (1 + markup_pct/100) = displayed price
3. - Promo discount: displayed × discount% = after_promo
4. - Wallet balance (user-chosen amount, capped at after_promo)
5. = Gateway charge (CryptoBot invoice amount)
```

**Commissions always use BASE price** (not discounted). If promo+wallet fully cover payment, complete immediately without gateway.

## Database Schema

### New Tables (10)

#### `system_config`
Admin-configurable settings (key-value JSONB).
- `key VARCHAR(100) PK`, `value JSONB NOT NULL`, `description TEXT`, `updated_at`, `updated_by → admin_users`

#### `wallets`
- `id UUID PK`, `user_id UUID UNIQUE → mobile_users`, `balance NUMERIC(20,8) DEFAULT 0`, `currency VARCHAR(10) DEFAULT 'USD'`, `frozen NUMERIC(20,8) DEFAULT 0`, `created_at`, `updated_at`
- CHECK: balance >= 0, frozen >= 0

#### `wallet_transactions`
Full ledger of wallet operations.
- `id UUID PK`, `wallet_id → wallets`, `user_id → mobile_users`, `type` (credit|debit), `amount NUMERIC(20,8)`, `currency`, `balance_after`, `reason` (referral_commission|partner_earning|partner_markup|admin_topup|subscription_payment|withdrawal|withdrawal_fee|refund|adjustment), `reference_type`, `reference_id`, `description`, `created_at`

#### `withdrawal_requests`
- `id UUID PK`, `user_id → mobile_users`, `wallet_id → wallets`, `amount`, `currency`, `method` (cryptobot|manual), `status` (pending|processing|completed|failed|cancelled), `external_id`, `admin_note`, `processed_at`, `processed_by → admin_users`, `wallet_tx_id → wallet_transactions`, `created_at`, `updated_at`

#### `invite_codes`
- `id UUID PK`, `code VARCHAR(20) UNIQUE`, `owner_user_id → mobile_users`, `free_days INT`, `plan_id → subscription_plans` (nullable), `source` (purchase|admin_grant), `source_payment_id → payments` (nullable), `is_used BOOL DEFAULT FALSE`, `used_by_user_id → mobile_users`, `used_at`, `expires_at`, `created_at`

#### `promo_codes`
- `id UUID PK`, `code VARCHAR(50) UNIQUE`, `discount_type` (percent|fixed), `discount_value NUMERIC(10,2)`, `currency`, `max_uses INT` (NULL=unlimited), `current_uses INT DEFAULT 0`, `is_single_use BOOL`, `plan_ids UUID[]` (NULL=all plans), `min_amount`, `expires_at` (NULL=no expiry), `is_active BOOL`, `created_by → admin_users`, `created_at`, `updated_at`

#### `promo_code_usages`
- `id UUID PK`, `promo_code_id → promo_codes`, `user_id → mobile_users`, `payment_id → payments`, `discount_applied`, `created_at`

#### `partner_codes`
- `id UUID PK`, `code VARCHAR(30) UNIQUE`, `partner_user_id → mobile_users`, `markup_pct NUMERIC(5,2) DEFAULT 0`, `is_active BOOL`, `created_at`, `updated_at`
- CHECK: markup_pct >= 0

#### `partner_earnings`
- `id UUID PK`, `partner_user_id → mobile_users`, `client_user_id → mobile_users`, `payment_id → payments`, `partner_code_id → partner_codes`, `base_price`, `markup_amount`, `commission_pct`, `commission_amount`, `total_earning`, `currency`, `wallet_tx_id → wallet_transactions`, `created_at`

#### `referral_commissions`
- `id UUID PK`, `referrer_user_id → mobile_users`, `referred_user_id → mobile_users`, `payment_id → payments`, `commission_rate NUMERIC(5,4)`, `base_amount`, `commission_amount`, `currency`, `wallet_tx_id → wallet_transactions`, `created_at`

### Modified Tables

#### `mobile_users` — add columns:
- `referral_code VARCHAR(12) UNIQUE` — permanent unique referral code
- `referred_by_user_id UUID → mobile_users` — who referred this user
- `partner_user_id UUID → mobile_users` — bound partner (permanent, one-time set)
- `is_partner BOOL DEFAULT FALSE`
- `partner_promoted_at TIMESTAMPTZ`

#### `payments` — add columns:
- `plan_id UUID → subscription_plans`
- `promo_code_id UUID → promo_codes`
- `discount_amount NUMERIC(20,8) DEFAULT 0`
- `wallet_amount_used NUMERIC(20,8) DEFAULT 0`
- `final_amount NUMERIC(20,8)` — actual gateway charge
- `partner_code_id UUID → partner_codes`

## Admin Config Keys (`system_config`)

| Key | Value Example |
|-----|--------------|
| `invite.plan_rules` | `{"rules": [{"plan_id": "...", "invite_count": 3, "free_days": 7}]}` |
| `invite.default_expiry_days` | `{"days": 30}` |
| `referral.commission_rate` | `{"rate": 0.10}` |
| `referral.duration_mode` | `{"mode": "indefinite"}` or `{"mode": "time_limited", "months": 12}` or `{"mode": "payment_count", "count": 5}` or `{"mode": "first_payment_only"}` |
| `referral.enabled` | `{"enabled": true}` |
| `partner.max_markup_pct` | `{"max_pct": 300}` |
| `partner.base_commission_pct` | `{"pct": 10}` |
| `partner.tiers` | `{"tiers": [{"min_clients": 0, "commission_pct": 20}, {"min_clients": 50, "commission_pct": 30}, {"min_clients": 1000, "commission_pct": 50}]}` |
| `wallet.min_withdrawal` | `{"amount": 5.0, "currency": "USD"}` |
| `wallet.withdrawal_enabled` | `{"enabled": true}` |
| `wallet.withdrawal_fee_pct` | `{"pct": 0}` |

## API Endpoints (~40 total)

### Invite Codes
- `POST /api/v1/invites/redeem` — Redeem invite code during registration
- `GET /api/v1/invites/my` — List my invite codes
- `POST /api/v1/admin/invite-codes` — Admin: create invite codes for user
- `GET /api/v1/admin/invite-codes` — Admin: list all
- `DELETE /api/v1/admin/invite-codes/{id}` — Admin: revoke

### Referral (matches existing Flutter data source contract)
- `GET /api/v1/referral/status` — Feature availability check
- `GET /api/v1/referral/code` — Get my referral code
- `GET /api/v1/referral/stats` — Stats (total_invited, paid_users, earnings, balance)
- `GET /api/v1/referral/recent` — Recent referrals with status
- `GET /api/v1/admin/referral/config` — Admin: get config
- `PUT /api/v1/admin/referral/config` — Admin: update config
- `GET /api/v1/admin/referral/commissions` — Admin: list commissions

### Promo Codes
- `POST /api/v1/promo/validate` — Validate promo code (returns discount preview)
- `POST /api/v1/admin/promo-codes` — Admin: create
- `GET /api/v1/admin/promo-codes` — Admin: list
- `GET /api/v1/admin/promo-codes/{id}` — Admin: details + stats
- `PUT /api/v1/admin/promo-codes/{id}` — Admin: update
- `DELETE /api/v1/admin/promo-codes/{id}` — Admin: deactivate
- `GET /api/v1/admin/promo-codes/{id}/usages` — Admin: usage log

### Partners
- `POST /api/v1/partner/codes` — Partner: create code
- `GET /api/v1/partner/codes` — Partner: list own codes
- `PUT /api/v1/partner/codes/{id}` — Partner: update markup
- `GET /api/v1/partner/dashboard` — Partner: earnings summary, client count, tier
- `GET /api/v1/partner/earnings` — Partner: paginated earnings history
- `GET /api/v1/partner/clients` — Partner: list bound clients
- `POST /api/v1/partner/bind` — Client: bind to partner code (permanent, one-time)
- `POST /api/v1/admin/partners/promote` — Admin: promote user to partner
- `DELETE /api/v1/admin/partners/{user_id}/demote` — Admin: demote
- `GET /api/v1/admin/partners` — Admin: list all partners
- `PUT /api/v1/admin/partners/config` — Admin: update tiers/max markup

### Wallet
- `GET /api/v1/wallet` — My balance
- `GET /api/v1/wallet/transactions` — Transaction history (paginated)
- `POST /api/v1/wallet/withdraw` — Request withdrawal
- `GET /api/v1/wallet/withdrawals` — My withdrawal requests
- `POST /api/v1/admin/wallets/{user_id}/topup` — Admin: manual top-up
- `GET /api/v1/admin/wallets/{user_id}` — Admin: view wallet
- `GET /api/v1/admin/withdrawals` — Admin: list pending withdrawals
- `PUT /api/v1/admin/withdrawals/{id}/approve` — Admin: approve
- `PUT /api/v1/admin/withdrawals/{id}/reject` — Admin: reject

### Checkout
- `POST /api/v1/payments/checkout` — Unified: plan + promo + wallet + partner resolution

## Key Business Flows

### Payment Webhook (after successful payment)
1. Activate VPN subscription via Remnawave API
2. Generate invite codes based on plan rules in `system_config`
3. Calculate referral commission (check duration policy eligibility first)
4. Calculate partner earnings (markup + tiered commission)
5. Credit wallets for referrer and partner
6. Record all in `referral_commissions` and `partner_earnings`

### Wallet Freeze for Pending Payments
- At checkout: freeze wallet amount (not debit)
- On webhook success: debit frozen amount
- On payment expiry (30min cron): unfreeze
- Prevents "wallet charged but nothing received"

### Referral Eligibility Check (pseudocode)
```python
if mode == "indefinite": return True
if mode == "first_payment_only": return commission_count == 0
if mode == "payment_count": return commission_count < max_count
if mode == "time_limited": return (now - referral_created_at) < months * 30 days
```

## Edge Cases

- **Partner 0% markup**: Valid. Partner earns only tier commission.
- **Promo covers entire amount**: Complete immediately, no gateway. Commissions still generated from base price.
- **Partner code + promo + referral**: All apply simultaneously. Partner gets markup+commission, referrer gets %, promo reduces user's displayed price.
- **Self-referral prevention**: Check at registration that invite owner != new user (by email).
- **Partner binding is permanent**: 409 if already bound. Admin can override via DB only.
- **Concurrent wallet ops**: SELECT ... FOR UPDATE on wallet row.

## New Files Structure

### Domain Layer (`backend/src/domain/`)
- `entities/`: `invite_code.py`, `referral.py`, `promo_code.py`, `partner.py`, `wallet.py`
- `repositories/`: `invite_code_repository.py`, `promo_code_repository.py`, `partner_repository.py`, `wallet_repository.py`
- `enums/enums.py` — add: InviteSource, DiscountType, WalletTxType, WalletTxReason, WithdrawalStatus, WithdrawalMethod, ReferralDurationMode
- `exceptions/domain_errors.py` — add: InviteCodeNotFoundError, PromoCodeInvalidError, InsufficientWalletBalanceError, etc.

### Infrastructure Layer (`backend/src/infrastructure/database/`)
- `models/`: `invite_code_model.py`, `referral_commission_model.py`, `promo_code_model.py`, `promo_code_usage_model.py`, `partner_code_model.py`, `partner_earning_model.py`, `wallet_model.py`, `wallet_transaction_model.py`, `withdrawal_request_model.py`, `system_config_model.py`
- `repositories/`: `invite_code_repo.py`, `referral_commission_repo.py`, `promo_code_repo.py`, `partner_repo.py`, `wallet_repo.py`, `withdrawal_repo.py`, `system_config_repo.py`
- Modify: `mobile_user_model.py`, `payment_model.py`

### Application Layer (`backend/src/application/`)
- `services/`: `config_service.py`, `wallet_service.py`
- `use_cases/invites/`: `redeem_invite.py`, `generate_invites_for_payment.py`, `admin_create_invite.py`
- `use_cases/referrals/`: `get_referral_code.py`, `get_referral_stats.py`, `process_referral_commission.py`
- `use_cases/promo_codes/`: `validate_promo.py`, `admin_manage_promo.py`
- `use_cases/partners/`: `create_partner_code.py`, `bind_partner.py`, `partner_dashboard.py`, `process_partner_earning.py`
- `use_cases/wallet/`: `get_balance.py`, `request_withdrawal.py`, `process_withdrawal.py`, `admin_topup.py`
- `use_cases/payments/checkout.py` — unified checkout
- Modify: `use_cases/payments/payment_webhook.py` — add commission/invite generation
- `dto/`: `invite_dto.py`, `referral_dto.py`, `promo_dto.py`, `partner_dto.py`, `wallet_dto.py`, `checkout_dto.py`

### Presentation Layer (`backend/src/presentation/api/v1/`)
- `invites/routes.py`, `invites/schemas.py`
- `referral/routes.py`, `referral/schemas.py`
- `promo_codes/routes.py`, `promo_codes/schemas.py`
- `partners/routes.py`, `partners/schemas.py`
- `wallet/routes.py`, `wallet/schemas.py`
- Modify: `router.py` — register new routers

### Migrations (`backend/alembic/versions/`)
8 migration files in dependency order:
1. `add_system_config.py`
2. `add_wallet_tables.py` (wallets + wallet_transactions)
3. `modify_mobile_users_codes.py` (referral_code, referred_by, partner_user_id, is_partner)
4. `modify_payments_codes.py` (plan_id, promo_code_id, discount_amount, wallet_amount_used, final_amount, partner_code_id)
5. `add_invite_codes.py`
6. `add_promo_codes.py` (promo_codes + promo_code_usages)
7. `add_partner_tables.py` (partner_codes + partner_earnings)
8. `add_referral_commissions.py`
9. `add_withdrawal_requests.py`

## Implementation Phases

### Phase 1: Foundation
- `system_config` table + ConfigService
- Wallet tables + WalletService (credit/debit/freeze/unfreeze)
- Column additions to `mobile_users` and `payments`

### Phase 2: Invite Codes
- `invite_codes` table + domain + repo + use cases
- Registration flow modification (accept invite_code)
- Post-payment invite generation in webhook

### Phase 3: Promo Codes
- `promo_codes` + `promo_code_usages` tables
- Admin CRUD endpoints
- Promo validation

### Phase 4: Referral System
- Referral code generation on user creation
- `referral_commissions` table
- Commission calculation in webhook
- Mobile API endpoints (matching Flutter data source)

### Phase 5: Partner System
- `partner_codes` + `partner_earnings` tables
- Partner promotion + code CRUD
- Earning calculation in webhook
- Partner dashboard endpoints

### Phase 6: Unified Checkout
- `CheckoutUseCase` combining all 4 code types + wallet
- Enhanced payment webhook with all post-payment logic
- Frozen wallet cleanup cron (30min TTL)

### Phase 7: Withdrawals
- `withdrawal_requests` table
- Withdrawal request + admin approval
- CryptoBot transfer integration

## Verification

1. **Unit tests**: Each use case tested in isolation with mocked repositories
2. **Integration tests**: Full checkout flow with all 4 codes + wallet (use test DB)
3. **Manual API test**: curl/httpie against local Docker stack
4. **Mobile integration**: Verify Flutter referral screen works with new endpoints
5. **Edge case tests**: Zero-gateway payment, expired promo, partner 0% markup, concurrent wallet ops
