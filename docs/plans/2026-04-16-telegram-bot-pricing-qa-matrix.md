# Telegram Bot Pricing QA Matrix

| Area | Scenario | Expected Result |
| --- | --- | --- |
| Bootstrap | New user opens `/start` | User is created in bot auth backend and linked to `mobile_users` |
| Catalog | User opens purchase flow | Only `Basic / Plus / Pro / Max` are shown |
| Hidden Plans | Public user opens purchase flow | `Start / Test / Development` are not shown |
| Periods | User selects a plan | Only seeded `30 / 90 / 180 / 365` periods appear for that plan |
| Add-ons | User selects `Basic` | `extra_device` can be incremented only up to the plan limit |
| Add-ons | User selects a plan without bot-supported add-ons | Flow skips directly to payment summary |
| Quote | User reaches payment step | Bot summary matches backend `gateway_amount` and selected add-ons |
| Commit | User taps `CryptoBot` | Pending payment is created and payment URL is returned |
| Polling | User taps `Check payment` before webhook | Bot shows `pending` state without losing FSM context |
| Completion | Webhook marks payment completed | Bot shows success and offers config delivery |
| Trial | Eligible user taps trial | Bot activates canonical `7d / 1 device / shared-only` trial |
| Trial | User with active paid plan taps trial | Bot returns `active_subscription` reason |
| Trial | User who already used trial taps trial | Bot returns `already_used` reason |
| Entitlements | User with trial opens connect menu | Bot treats `trial` as active access |
| Entitlements | User with paid plan opens connect menu | Bot shows active subscription CTA set |
| Admin | Admin opens bot plans view | Bot shows canonical catalog rows with visibility and duration |
| Regression | Referral/profile/config menus | Existing bot flows continue to work after pricing migration |
