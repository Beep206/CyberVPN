import { apiClient } from './client';
import type { AxiosResponse } from 'axios';
import type { components } from './generated/types';
import {
  privacyRequestsApi,
  type PrivacyRequestAcceptedResponse,
  type PrivacyRequestCreateRequest,
  type PrivacyRequestType,
} from './privacy-requests';

// Request interfaces
export interface LoginRequest {
  login_or_email?: string;
  email?: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  login: string;
  email?: string;
  password: string;
  locale?: string;
  tos_accepted: boolean;
  marketing_consent?: boolean;
}

export interface TelegramWidgetData {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

export interface VerifyOtpRequest {
  email: string;
  code: string;
}

export interface ResendOtpRequest {
  email: string;
  locale?: string;
}

// Response interfaces
export interface User {
  id: string;
  public_uid?: number | null;
  email: string | null;
  login?: string;
  telegram_id?: number | null;
  role: 'viewer' | 'user' | 'admin' | 'super_admin';
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
  sign_in_count?: number;
  current_sign_in_ip?: string | null;
  last_login_at?: string | null;
}

export type CustomerUser =
  components['schemas']['src__presentation__api__v1__mobile_auth__schemas__UserResponse'];

export interface AuthResponse {
  user: User;
  is_new_user?: boolean;
  requires_2fa?: boolean;
  tfa_token?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  requires_2fa: boolean;
  tfa_token: string | null;
  auth_realm_id?: string | null;
  auth_realm_key?: string | null;
  audience?: string | null;
  principal_type?: string | null;
  scope_family?: string | null;
}

export type WebRefreshResponse = components['schemas']['WebRefreshResponse'];

export interface VerifyOtpResponse extends TokenResponse {
  user: User;
}

export interface RegisterResponse {
  id: string;
  login: string;
  email: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  message: string;
}

export interface ResendOtpResponse {
  message: string;
  resends_remaining: number;
  next_resend_available_at?: string;
}

export interface OtpErrorResponse {
  detail: string;
  code?: string;
  attempts_remaining?: number;
  next_resend_available_at?: string;
}

let sessionRequest: Promise<AxiosResponse<User>> | null = null;

function fetchSessionOnce(): Promise<AxiosResponse<User>> {
  if (!sessionRequest) {
    const request = apiClient
      .get<User>('/auth/session')
      .finally(() => {
        if (sessionRequest === request) {
          sessionRequest = null;
        }
      });
    sessionRequest = request;
  }

  return sessionRequest;
}

function clearSessionRequestCache(): void {
  sessionRequest = null;
}

function createPrivacyIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }

  const suffix = Math.random().toString(16).slice(2, 14).padEnd(12, '0');
  return `00000000-0000-4000-8000-${suffix}`;
}

export type OAuthProvider = 'google' | 'github' | 'discord' | 'facebook' | 'apple' | 'microsoft' | 'twitter' | 'telegram';

export interface OAuthAuthorizeResponse {
  authorize_url: string;
  state: string;
}

export interface OAuthLoginUser {
  id: string;
  public_uid?: number | null;
  login: string;
  email: string | null;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
}

export interface OAuthLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: OAuthLoginUser;
  is_new_user: boolean;
  requires_2fa: boolean;
  tfa_token: string | null;
}

export interface OAuthCallbackRequest {
  code: string;
  state: string;
  redirect_uri?: string;
}

export interface TelegramMiniAppResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: OAuthLoginUser;
  is_new_user: boolean;
  requires_2fa: boolean;
  tfa_token: string | null;
}

export interface TelegramMagicLinkResponse {
  token: string;
  bot_url: string;
  deep_link_url?: string;
}

export interface TelegramMagicLinkLoginResult {
  user: OAuthLoginUser;
  is_new_user: boolean;
  requires_2fa: boolean;
  tfa_token: string | null;
}

export interface TelegramMagicLinkStatusResponse {
  status: 'pending' | 'completed' | 'expired';
  login_result?: TelegramMagicLinkLoginResult | null;
}

export interface TelegramAccountLinkResponse {
  token: string;
  bot_url: string;
  deep_link_url?: string | null;
  expires_in: number;
}

export interface TelegramAccountLinkStatusResponse {
  status: 'pending' | 'linked' | 'expired' | 'conflict';
  provider: 'telegram';
  provider_user_id?: string | null;
}

export interface BotLinkRequest {
  token: string;
}

export interface BotLinkResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: OAuthLoginUser;
  requires_2fa: boolean;
  tfa_token: string | null;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordRequest {
  email: string;
  code: string;
  new_password: string;
}

export interface ResetPasswordResponse {
  message: string;
}

export interface DeleteAccountResponse {
  message: string;
}

export type { PrivacyRequestType };
export type PrivacyRequestCreate = PrivacyRequestCreateRequest;
export type PrivacyRequestResponse = PrivacyRequestAcceptedResponse;

export interface MagicLinkRequest {
  email: string;
}

export interface MagicLinkResponse {
  message: string;
}

export interface MagicLinkVerifyRequest {
  token: string;
}

export interface MagicLinkVerifyResponse extends TokenResponse {
  user: User;
  requires_2fa?: boolean;
  tfa_token?: string | null;
}

export interface MagicLinkVerifyOtpRequest {
  email: string;
  code: string;
}

export type DeviceSessionListResponse = components['schemas']['DeviceSessionListResponse'];
export type DeviceSessionResponse =
  components['schemas']['src__presentation__api__v1__auth__schemas__DeviceSessionResponse'];
export type LogoutOthersResponse = components['schemas']['LogoutOthersResponse'];
export type RevokeDeviceResponse = components['schemas']['RevokeDeviceResponse'];

// Account linking types
export interface LinkedAccount {
  provider: string;
  provider_user_id: string;
}

export interface OAuthLinkResponse {
  status: 'linked' | 'unlinked';
  provider: string;
  provider_user_id?: string;
}

// Auth API functions
export const authApi = {
  /**
   * Login with email and password
   * POST /api/v1/auth/login
   */
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login', {
      login_or_email: data.login_or_email ?? data.email ?? '',
      password: data.password,
      remember_me: data.remember_me,
    }),

  /**
   * Register new user with email and password
   * POST /api/v1/auth/register
   * Returns user with is_active=false, is_email_verified=false
   */
  register: (data: RegisterRequest) =>
    apiClient.post<RegisterResponse>('/auth/register', data),

  /**
   * Verify OTP code for email verification
   * POST /api/v1/auth/verify-otp
   * On success, returns tokens (auto-login) and activates user
   */
  verifyOtp: (data: VerifyOtpRequest) =>
    apiClient.post<VerifyOtpResponse>('/auth/verify-otp', data),

  /**
   * Resend OTP verification code
   * POST /api/v1/auth/resend-otp
   * Uses Brevo (secondary provider) for resend requests
   */
  resendOtp: (data: ResendOtpRequest) =>
    apiClient.post<ResendOtpResponse>('/auth/resend-otp', data),

  /**
   * Logout current user
   * POST /api/v1/auth/logout
   */
  logout: () =>
    apiClient.post('/auth/logout'),

  /**
   * Refresh access token using refresh token cookie
   * POST /api/v1/auth/refresh
   */
  refresh: () =>
    apiClient.post<WebRefreshResponse>('/auth/refresh'),

  /**
   * Get current authenticated user
   * GET /api/v1/auth/me
   */
  me: () =>
    apiClient.get<User>('/auth/me/'),

  /**
   * Get current authenticated customer profile
   * GET /api/v1/mobile/auth/me
   */
  customerMe: () =>
    apiClient.get<CustomerUser>('/mobile/auth/me'),

  /**
   * Get current authenticated session (redirect-loop-safe alias)
   * GET /api/v1/auth/session
   */
  session: () =>
    fetchSessionOnce(),

  clearSessionRequestCache: () => {
    clearSessionRequestCache();
  },

  /**
   * Authenticate via Telegram Login Widget
   * POST /api/v1/auth/oauth2/telegram/callback
   */
  telegramWidget: (data: TelegramWidgetData) =>
    apiClient.post<AuthResponse>('/auth/oauth2/telegram/callback', data),

  /**
   * Authenticate via modern Telegram Web Login (2026 approach)
   * POST /api/v1/auth/telegram/web
   */
  telegramWebLogin: (data: TelegramWidgetData) =>
    apiClient.post<AuthResponse>('/auth/telegram/web', data),

  /**
   * Authenticate via Telegram Mini App initData
   * POST /api/v1/auth/telegram/miniapp
   */
  telegramMiniApp: (initData: string) =>
    apiClient.post<TelegramMiniAppResponse>('/auth/telegram/miniapp', { init_data: initData }),

  /**
   * Authenticate via Telegram bot deep-link token
   * POST /api/v1/auth/telegram/bot-link
   */
  telegramBotLink: (data: BotLinkRequest) =>
    apiClient.post<BotLinkResponse>('/auth/telegram/bot-link', data),

  /**
   * Get OAuth authorization URL for a provider
   * GET /api/v1/oauth/{provider}/login
   */
  oauthLoginAuthorize: (provider: OAuthProvider, redirectUri?: string) =>
    apiClient.get<OAuthAuthorizeResponse>(`/oauth/${provider}/login`, {
      params: redirectUri ? { redirect_uri: redirectUri } : undefined,
    }),

  /**
   * Complete OAuth login callback
   * POST /api/v1/oauth/{provider}/login/callback
   */
  oauthLoginCallback: (provider: OAuthProvider, data: OAuthCallbackRequest) =>
    apiClient.post<OAuthLoginResponse>(`/oauth/${provider}/login/callback`, data),

  /**
   * Request password reset (forgot password)
   * POST /api/v1/auth/forgot-password
   * Always returns success to prevent email enumeration
   */
  forgotPassword: (data: ForgotPasswordRequest) =>
    apiClient.post<ForgotPasswordResponse>('/auth/forgot-password', data),

  /**
   * Reset password with OTP code
   * POST /api/v1/auth/reset-password
   */
  resetPassword: (data: ResetPasswordRequest) =>
    apiClient.post<ResetPasswordResponse>('/auth/reset-password', data),

  /**
   * Request magic link for passwordless login
   * POST /api/v1/auth/magic-link
   */
  requestMagicLink: (data: MagicLinkRequest) =>
    apiClient.post<MagicLinkResponse>('/auth/magic-link', data),

  /**
   * Verify magic link token and get JWT tokens + user data
   * POST /api/v1/auth/magic-link/verify
   */
  verifyMagicLink: (data: MagicLinkVerifyRequest) =>
    apiClient.post<MagicLinkVerifyResponse>('/auth/magic-link/verify', data),

  /**
   * Verify magic link OTP code and get JWT tokens + user data
   * POST /api/v1/auth/magic-link/verify-otp
   */
  verifyMagicLinkOtp: (data: MagicLinkVerifyOtpRequest) =>
    apiClient.post<MagicLinkVerifyResponse>('/auth/magic-link/verify-otp', data),

  /**
   * Get Telegram OAuth authorize URL for account linking (authenticated)
   * GET /api/v1/oauth/telegram/authorize
   */
  telegramLinkAuthorize: (redirectUri: string) =>
    apiClient.get<OAuthAuthorizeResponse>('/oauth/telegram/authorize', {
      params: { redirect_uri: redirectUri },
    }),

  /**
   * Link Telegram account via OAuth callback (authenticated)
   * POST /api/v1/oauth/telegram/callback
   */
  telegramLinkCallback: (data: TelegramWidgetData & { state: string }) =>
    apiClient.post<OAuthLinkResponse>('/oauth/telegram/callback', data),

  /**
   * Unlink an OAuth provider from the current user (authenticated)
   * DELETE /api/v1/oauth/{provider}
   */
  unlinkProvider: (provider: OAuthProvider) =>
    apiClient.delete<OAuthLinkResponse>(`/oauth/${provider}`),

  /**
   * Delete the current user's account permanently
   * DELETE /api/v1/auth/me
   * Requires JWT auth. Returns { message: "Account has been deleted" }
   */
  deleteAccount: () =>
    apiClient.delete<DeleteAccountResponse>('/auth/me'),

  /**
   * Delete the current customer/mobile account permanently for Mini App flows.
   * DELETE /api/v1/mobile/auth/me
   */
  deleteMobileAccount: () =>
    apiClient.delete<DeleteAccountResponse>('/mobile/auth/me'),

  /**
   * Open a manual S1 privacy request for account deletion or data export.
   * POST /api/v1/auth/me/privacy-requests
   */
  requestPrivacyAction: (payload: PrivacyRequestCreate, idempotencyKey?: string) =>
    privacyRequestsApi.create(payload, idempotencyKey ?? createPrivacyIdempotencyKey()),

  /**
   * Request a manual S1 account-data export.
   * POST /api/v1/auth/me/privacy-requests
   */
  requestDataExport: (notes?: string | null) =>
    authApi.requestPrivacyAction({
      request_type: 'data_export',
      notes: notes ?? null,
    }),

  /**
   * List all active devices/sessions for the authenticated user
   * GET /api/v1/auth/devices
   *
   * Returns all active sessions with device info, IP, user agent, and is_current flag.
   */
  listDevices: () =>
    apiClient.get<DeviceSessionListResponse>('/auth/devices'),

  /**
   * Remote logout for all devices except the current one.
   * POST /api/v1/auth/devices/logout-others
   */
  logoutOtherDevices: () =>
    apiClient.post<LogoutOthersResponse>('/auth/devices/logout-others'),

  /**
   * Remote logout for a specific device
   * DELETE /api/v1/auth/devices/{device_id}
   *
   * Revokes the session for the specified device.
   *
   * @param deviceId - Device ID to logout
   * @throws 404 - Device not found
   */
  logoutDevice: (deviceId: string) =>
    apiClient.delete<RevokeDeviceResponse>(`/auth/devices/${deviceId}`),

  /**
   * Request a magic link for Telegram Login
   * GET /api/v1/oauth/telegram/magic-link
   */
  requestTelegramMagicLink: () =>
    apiClient.get<TelegramMagicLinkResponse>('/oauth/telegram/magic-link'),

  /**
   * Poll status of Telegram Magic Link
   * GET /api/v1/oauth/telegram/magic-link/{token}/status
   */
  pollTelegramMagicLinkStatus: (token: string) =>
    apiClient.get<TelegramMagicLinkStatusResponse>(`/oauth/telegram/magic-link/${token}/status`),

  /**
   * Request a Telegram account-linking session for the current authenticated user
   * POST /api/v1/oauth/telegram/account-link/magic-link
   */
  requestTelegramAccountLink: () =>
    apiClient.post<TelegramAccountLinkResponse>('/oauth/telegram/account-link/magic-link'),

  /**
   * Poll and finalize Telegram account-linking status
   * GET /api/v1/oauth/telegram/account-link/magic-link/{token}/status
   */
  pollTelegramAccountLinkStatus: (token: string) =>
    apiClient.get<TelegramAccountLinkStatusResponse>(
      `/oauth/telegram/account-link/magic-link/${token}/status`,
    ),
};
