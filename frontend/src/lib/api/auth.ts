import { apiClient } from './client';

// Request interfaces
export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  login: string;
  email: string;
  password: string;
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
}

// Response interfaces
export interface User {
  id: string;
  email: string;
  login?: string;
  telegram_id?: number;
  role: 'viewer' | 'user' | 'admin' | 'super_admin';
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
}

export interface AuthResponse {
  user: User;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface VerifyOtpResponse extends TokenResponse {
  user: User;
}

export interface RegisterResponse {
  id: string;
  login: string;
  email: string;
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

// Auth API functions
export const authApi = {
  /**
   * Login with email and password
   * POST /api/v1/auth/login
   */
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', data),

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
    apiClient.post('/auth/refresh'),

  /**
   * Get current authenticated user
   * GET /api/v1/auth/me
   */
  me: () =>
    apiClient.get<User>('/auth/me'),

  /**
   * Authenticate via Telegram Login Widget
   * POST /api/v1/auth/oauth2/telegram/callback
   */
  telegramWidget: (data: TelegramWidgetData) =>
    apiClient.post<AuthResponse>('/auth/oauth2/telegram/callback', data),

  /**
   * Authenticate via Telegram Mini App initData
   * POST /api/v1/auth/telegram/miniapp
   */
  telegramMiniApp: (initData: string) =>
    apiClient.post<AuthResponse>('/auth/telegram/miniapp', { init_data: initData }),
};
