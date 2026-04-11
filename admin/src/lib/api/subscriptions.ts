import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type SubscriptionsResponse = operations['list_subscription_templates_api_v1_subscriptions__get']['responses'][200]['content']['application/json'];
type CreateSubscriptionTemplateRequest =
  operations['create_subscription_template_api_v1_subscriptions__post']['requestBody']['content']['application/json'];
type CreateSubscriptionTemplateResponse =
  operations['create_subscription_template_api_v1_subscriptions__post']['responses'][200]['content']['application/json'];
type SubscriptionResponse = operations['get_subscription_template_api_v1_subscriptions__uuid__get']['responses'][200]['content']['application/json'];
type UpdateSubscriptionTemplateRequest =
  operations['update_subscription_template_api_v1_subscriptions__uuid__put']['requestBody']['content']['application/json'];
type UpdateSubscriptionTemplateResponse =
  operations['update_subscription_template_api_v1_subscriptions__uuid__put']['responses'][200]['content']['application/json'];
type DeleteSubscriptionTemplateResponse =
  operations['delete_subscription_template_api_v1_subscriptions__uuid__delete']['responses'][200]['content']['application/json'];
type UserConfigResponse = operations['generate_config_api_v1_subscriptions_config__user_uuid__get']['responses'][200]['content']['application/json'];

// Manual types for endpoints not in generated types
type CancelSubscriptionResponse = {
  message: string;
  cancelled_at: string;
};

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
   * Create a new subscription template.
   * POST /api/v1/subscriptions/
   */
  create: (data: CreateSubscriptionTemplateRequest) =>
    apiClient.post<CreateSubscriptionTemplateResponse>('/subscriptions/', data),

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
   * Update a subscription template.
   * PUT /api/v1/subscriptions/{uuid}
   */
  update: (uuid: string, data: UpdateSubscriptionTemplateRequest) =>
    apiClient.put<UpdateSubscriptionTemplateResponse>(`/subscriptions/${uuid}`, data),

  /**
   * Delete a subscription template.
   * DELETE /api/v1/subscriptions/{uuid}
   */
  remove: (uuid: string) =>
    apiClient.delete<DeleteSubscriptionTemplateResponse>(`/subscriptions/${uuid}`),

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
