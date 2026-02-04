import { apiClient } from './client';

// Request interfaces
export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
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

// Response interfaces
export interface User {
  id: string;
  email: string;
  telegram_id?: number;
  role: 'user' | 'admin' | 'super_admin';
  created_at: string;
}

export interface AuthResponse {
  user: User;
}

// Auth API functions
export const authApi = {
  /**
   * Login with email and password
   * POST /api/v1/auth/login
   */
  login: (data: LoginRequest) =>
    apiClient.post<AuthResponse>('/auth/login', data),

  /**
   * Register new user with email and password
   * POST /api/v1/auth/register
   */
  register: (data: RegisterRequest) =>
    apiClient.post<AuthResponse>('/auth/register', data),

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
