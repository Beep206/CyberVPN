import type { AxiosRequestConfig } from 'axios';
import { apiClient } from './client';
import type { operations } from './generated/types';

type TelegramUserResponse =
  operations['get_telegram_user_api_v1_telegram_user__telegram_id__get']['responses'][200]['content']['application/json'];
type CreateSubscriptionRequest =
  operations['create_subscription_api_v1_telegram_user__telegram_id__subscription_post']['requestBody']['content']['application/json'];
type TelegramConfigResponse =
  operations['get_user_config_api_v1_telegram_user__telegram_id__config_get']['responses'][200]['content']['application/json'];
type GenerateLoginLinkRequest =
  operations['generate_login_link_api_v1_auth_telegram_generate_login_link_post']['requestBody']['content']['application/json'];
type GenerateLoginLinkResponse =
  operations['generate_login_link_api_v1_auth_telegram_generate_login_link_post']['responses'][200]['content']['application/json'];
type NotificationPreferencesResponse =
  operations['get_notification_preferences_api_v1_users_me_notifications_get']['responses'][200]['content']['application/json'];
type NotificationPreferencesUpdateRequest =
  operations['update_notification_preferences_api_v1_users_me_notifications_patch']['requestBody']['content']['application/json'];
type FcmTokenRequest =
  operations['register_fcm_token_api_v1_users_me_fcm_token_post']['requestBody']['content']['application/json'];
type FcmTokenResponse =
  operations['register_fcm_token_api_v1_users_me_fcm_token_post']['responses'][201]['content']['application/json'];
type FcmTokenDeleteRequest =
  operations['unregister_fcm_token_api_v1_users_me_fcm_token_delete']['requestBody']['content']['application/json'];
type WsTicketResponse =
  operations['create_ws_ticket_api_v1_ws_ticket_post']['responses'][200]['content']['application/json'];
type TelegramBotAccessSettingsResponse =
  operations['get_bot_access_settings_api_v1_telegram_bot_settings_access_get']['responses'][200]['content']['application/json'];
type TelegramBotPlansResponse =
  operations['get_bot_plans_api_v1_telegram_bot_plans_get']['responses'][200]['content']['application/json'];
type TelegramBotUserResponse =
  operations['get_bot_user_api_v1_telegram_bot_user__telegram_id__get']['responses'][200]['content']['application/json'];
type TelegramBotUserCreateRequest =
  operations['create_or_bootstrap_bot_user_api_v1_telegram_bot_user_post']['requestBody']['content']['application/json'];
type TelegramBotSubscriptionsResponse =
  operations['get_bot_user_subscriptions_api_v1_telegram_bot_user__telegram_id__subscriptions_get']['responses'][200]['content']['application/json'];
type TelegramBotTrialStatusResponse =
  operations['get_bot_user_trial_status_api_v1_telegram_bot_user__telegram_id__trial_status_get']['responses'][200]['content']['application/json'];
type TelegramBotReferralStatsResponse =
  operations['get_bot_user_referral_stats_api_v1_telegram_bot_user__telegram_id__referral_stats_get']['responses'][200]['content']['application/json'];
type TelegramBotConfigResponse =
  operations['get_bot_user_config_api_v1_telegram_bot_user__telegram_id__config_get']['responses'][200]['content']['application/json'];

function requestAppRoute<T>(config: AxiosRequestConfig) {
  return apiClient.request<T>({
    ...config,
    baseURL: '',
  });
}

/**
 * Integrations API client
 * Covers Telegram operator tools, push diagnostics, and realtime ticket flows.
 */
export const integrationsApi = {
  /**
   * Get Telegram-linked VPN user by Telegram ID.
   * GET /api/v1/telegram/user/{telegram_id}
   */
  getTelegramUser: (telegramId: number) =>
    apiClient.get<TelegramUserResponse>(`/telegram/user/${telegramId}`),

  /**
   * Get VPN config for a Telegram-linked user.
   * GET /api/v1/telegram/user/{telegram_id}/config
   */
  getTelegramConfig: (telegramId: number) =>
    apiClient.get<TelegramConfigResponse>(`/telegram/user/${telegramId}/config`),

  /**
   * Create a subscription for a Telegram-linked user.
   * POST /api/v1/telegram/user/{telegram_id}/subscription
   */
  createTelegramSubscription: (
    telegramId: number,
    data: CreateSubscriptionRequest,
  ) => apiClient.post<Record<string, unknown>>(
    `/telegram/user/${telegramId}/subscription`,
    data,
  ),

  /**
   * Generate one-time Telegram bot login link for a user.
   * POST /api/v1/auth/telegram/generate-login-link
   */
  generateTelegramLoginLink: (data: GenerateLoginLinkRequest) =>
    apiClient.post<GenerateLoginLinkResponse>(
      '/auth/telegram/generate-login-link',
      data,
    ),

  /**
   * Read the current operator notification preferences.
   * GET /api/v1/users/me/notifications
   */
  getNotificationPreferences: () =>
    apiClient.get<NotificationPreferencesResponse>('/users/me/notifications'),

  /**
   * Update the current operator notification preferences.
   * PATCH /api/v1/users/me/notifications
   */
  updateNotificationPreferences: (
    data: NotificationPreferencesUpdateRequest,
  ) => apiClient.patch<NotificationPreferencesResponse>(
    '/users/me/notifications',
    data,
  ),

  /**
   * Register an FCM token for diagnostics or device bootstrap.
   * POST /api/v1/users/me/fcm-token
   */
  registerFcmToken: (data: FcmTokenRequest) =>
    apiClient.post<FcmTokenResponse>('/users/me/fcm-token', data),

  /**
   * Remove an FCM token for a specific device.
   * DELETE /api/v1/users/me/fcm-token
   */
  unregisterFcmToken: (data: FcmTokenDeleteRequest) =>
    apiClient.delete<void>('/users/me/fcm-token', { data }),

  /**
   * Create a single-use WebSocket ticket for realtime monitoring topics.
   * POST /api/v1/ws/ticket
   */
  createRealtimeTicket: () =>
    apiClient.post<WsTicketResponse>('/ws/ticket'),

  /**
   * Read Telegram bot access settings through the admin BFF proxy.
   * GET /api/integrations/telegram/bot/settings/access
   */
  getTelegramBotAccessSettings: () =>
    requestAppRoute<TelegramBotAccessSettingsResponse>({
      method: 'GET',
      url: '/api/integrations/telegram/bot/settings/access',
    }),

  /**
   * Read the bot-facing plan catalog through the admin BFF proxy.
   * GET /api/integrations/telegram/bot/plans
   */
  getTelegramBotPlans: () =>
    requestAppRoute<TelegramBotPlansResponse>({
      method: 'GET',
      url: '/api/integrations/telegram/bot/plans',
    }),

  /**
   * Read the Telegram bot-facing user payload through the admin BFF proxy.
   * GET /api/integrations/telegram/bot/user/{telegram_id}
   */
  getTelegramBotUser: (telegramId: number) =>
    requestAppRoute<TelegramBotUserResponse>({
      method: 'GET',
      url: `/api/integrations/telegram/bot/user/${telegramId}`,
    }),

  /**
   * Create or refresh a Telegram bot user through the admin BFF proxy.
   * POST /api/integrations/telegram/bot/user
   */
  bootstrapTelegramBotUser: (data: TelegramBotUserCreateRequest) =>
    requestAppRoute<TelegramBotUserResponse>({
      method: 'POST',
      url: '/api/integrations/telegram/bot/user',
      data,
    }),

  /**
   * Read bot-facing subscriptions for a Telegram user.
   * GET /api/integrations/telegram/bot/user/{telegram_id}/subscriptions
   */
  getTelegramBotSubscriptions: (telegramId: number) =>
    requestAppRoute<TelegramBotSubscriptionsResponse>({
      method: 'GET',
      url: `/api/integrations/telegram/bot/user/${telegramId}/subscriptions`,
    }),

  /**
   * Read bot-facing trial status for a Telegram user.
   * GET /api/integrations/telegram/bot/user/{telegram_id}/trial-status
   */
  getTelegramBotTrialStatus: (telegramId: number) =>
    requestAppRoute<TelegramBotTrialStatusResponse>({
      method: 'GET',
      url: `/api/integrations/telegram/bot/user/${telegramId}/trial-status`,
    }),

  /**
   * Activate a Telegram bot user trial.
   * POST /api/integrations/telegram/bot/user/{telegram_id}/trial/activate
   */
  activateTelegramBotTrial: (telegramId: number) =>
    requestAppRoute<TelegramBotTrialStatusResponse>({
      method: 'POST',
      url: `/api/integrations/telegram/bot/user/${telegramId}/trial/activate`,
    }),

  /**
   * Read bot-facing referral stats for a Telegram user.
   * GET /api/integrations/telegram/bot/user/{telegram_id}/referral-stats
   */
  getTelegramBotReferralStats: (telegramId: number) =>
    requestAppRoute<TelegramBotReferralStatsResponse>({
      method: 'GET',
      url: `/api/integrations/telegram/bot/user/${telegramId}/referral-stats`,
    }),

  /**
   * Read bot-facing VPN config for a Telegram user.
   * GET /api/integrations/telegram/bot/user/{telegram_id}/config
   */
  getTelegramBotConfig: (telegramId: number) =>
    requestAppRoute<TelegramBotConfigResponse>({
      method: 'GET',
      url: `/api/integrations/telegram/bot/user/${telegramId}/config`,
    }),
};

export type {
  CreateSubscriptionRequest,
  FcmTokenDeleteRequest,
  FcmTokenRequest,
  FcmTokenResponse,
  GenerateLoginLinkRequest,
  GenerateLoginLinkResponse,
  NotificationPreferencesResponse,
  NotificationPreferencesUpdateRequest,
  TelegramBotAccessSettingsResponse,
  TelegramBotConfigResponse,
  TelegramBotPlansResponse,
  TelegramBotReferralStatsResponse,
  TelegramBotSubscriptionsResponse,
  TelegramBotTrialStatusResponse,
  TelegramBotUserCreateRequest,
  TelegramBotUserResponse,
  TelegramConfigResponse,
  TelegramUserResponse,
  WsTicketResponse,
};
