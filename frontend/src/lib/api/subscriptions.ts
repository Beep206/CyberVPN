import { apiClient } from './client';
import type { operations } from './generated/types';

export type SubscriptionsResponse =
  operations['list_subscription_templates_api_v1_subscriptions__get']['responses'][200]['content']['application/json'];
export type SubscriptionResponse =
  operations['get_subscription_template_api_v1_subscriptions__uuid__get']['responses'][200]['content']['application/json'];
export type UserConfigResponse =
  operations['generate_config_api_v1_subscriptions_config__user_uuid__get']['responses'][200]['content']['application/json'];
export type CurrentEntitlementsResponse =
  operations['get_current_entitlements_api_v1_subscriptions_current_entitlements_get']['responses'][200]['content']['application/json'];
export type UpgradeSubscriptionRequest =
  operations['quote_subscription_upgrade_api_v1_subscriptions_current_upgrade_quote_post']['requestBody']['content']['application/json'];
export type QuoteUpgradeResponse =
  operations['quote_subscription_upgrade_api_v1_subscriptions_current_upgrade_quote_post']['responses'][200]['content']['application/json'];
export type CommitUpgradeResponse =
  operations['commit_subscription_upgrade_api_v1_subscriptions_current_upgrade_post']['responses'][200]['content']['application/json'];
export type PurchaseSubscriptionAddonsRequest =
  operations['quote_subscription_addons_api_v1_subscriptions_current_addons_quote_post']['requestBody']['content']['application/json'];
export type QuoteSubscriptionAddonsResponse =
  operations['quote_subscription_addons_api_v1_subscriptions_current_addons_quote_post']['responses'][200]['content']['application/json'];
export type PurchaseSubscriptionAddonsResponse =
  operations['purchase_subscription_addons_api_v1_subscriptions_current_addons_post']['responses'][200]['content']['application/json'];
type CancelSubscriptionResponse =
  operations['cancel_subscription_api_v1_subscriptions_cancel_post']['responses'][200]['content']['application/json'];

/**
 * Subscriptions API client
 * Manages user subscription plans, status, and VPN configurations
 */
export const subscriptionsApi = {
  /**
   * List all subscriptions for authenticated user
   * GET /api/v1/subscriptions/
   *
   * Returns all subscriptions (active, expired, cancelled) for the user.
   */
  list: () =>
    apiClient.get<SubscriptionsResponse>('/subscriptions/'),

  /**
   * Get subscription details by UUID
   * GET /api/v1/subscriptions/{uuid}
   *
   * Returns detailed information about a specific subscription including
   * plan details, expiration, and status.
   *
   * @param uuid - Subscription UUID
   * @throws 404 - Subscription not found
   */
  get: (uuid: string) =>
    apiClient.get<SubscriptionResponse>(`/subscriptions/${uuid}`),

  /**
   * Get VPN configuration for user
   * GET /api/v1/subscriptions/config/{user_uuid}
   *
   * Returns Remnawave VPN configuration including:
   * - Connection URLs
   * - Supported protocols
   * - Server locations
   * - Client credentials
   *
   * @param userUuid - User UUID
   * @throws 404 - User or config not found
   */
  getConfig: (userUuid: string) =>
    apiClient.get<UserConfigResponse>(`/subscriptions/config/${userUuid}`),

  /**
   * Read effective entitlements for the authenticated user's current plan.
   * GET /api/v1/subscriptions/current/entitlements
   */
  getCurrentEntitlements: () =>
    apiClient.get<CurrentEntitlementsResponse>('/subscriptions/current/entitlements'),

  /**
   * Quote a mid-cycle subscription upgrade.
   * POST /api/v1/subscriptions/current/upgrade/quote
   */
  quoteUpgrade: (data: UpgradeSubscriptionRequest) =>
    apiClient.post<QuoteUpgradeResponse>('/subscriptions/current/upgrade/quote', data),

  /**
   * Commit a mid-cycle subscription upgrade.
   * POST /api/v1/subscriptions/current/upgrade
   */
  commitUpgrade: (data: UpgradeSubscriptionRequest) =>
    apiClient.post<CommitUpgradeResponse>('/subscriptions/current/upgrade', data),

  /**
   * Quote add-ons on top of the active subscription.
   * POST /api/v1/subscriptions/current/addons/quote
   */
  quoteAddons: (data: PurchaseSubscriptionAddonsRequest) =>
    apiClient.post<QuoteSubscriptionAddonsResponse>('/subscriptions/current/addons/quote', data),

  /**
   * Purchase add-ons on top of the active subscription.
   * POST /api/v1/subscriptions/current/addons
   */
  purchaseAddons: (data: PurchaseSubscriptionAddonsRequest) =>
    apiClient.post<PurchaseSubscriptionAddonsResponse>('/subscriptions/current/addons', data),

  /**
   * Cancel active subscription
   * POST /api/v1/subscriptions/cancel
   *
   * Cancels the user's active subscription. The subscription will remain
   * active until the end of the current billing period.
   *
   * @returns Cancellation confirmation with timestamp
   * @throws 404 - No active subscription found
   * @throws 400 - Subscription already cancelled
   */
  cancel: () =>
    apiClient.post<CancelSubscriptionResponse>('/subscriptions/cancel'),
};
