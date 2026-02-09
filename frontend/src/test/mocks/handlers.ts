/**
 * MSW (Mock Service Worker) request handlers for CyberVPN API.
 *
 * These handlers intercept HTTP requests during tests and return
 * realistic mock responses that match the backend API contract.
 *
 * Covers:
 * - Auth endpoints (login, register, forgot-password, reset-password, delete-account, etc.)
 * - Server list endpoints
 * - User management endpoints
 */
import { http, HttpResponse } from 'msw';

// ---------------------------------------------------------------------------
// Helpers & Constants
// ---------------------------------------------------------------------------

const API_BASE = 'http://localhost:8000/api/v1';

/** Reusable mock user returned by /auth/me and embedded in token responses. */
export const MOCK_USER = {
  id: 'usr_test_001',
  email: 'testuser@cybervpn.io',
  login: 'testuser',
  telegram_id: null,
  role: 'user' as const,
  is_active: true,
  is_email_verified: true,
  created_at: '2025-06-01T12:00:00Z',
};

/** Reusable mock admin user. */
export const MOCK_ADMIN_USER = {
  id: 'usr_admin_001',
  email: 'admin@cybervpn.io',
  login: 'admin',
  telegram_id: 123456789,
  role: 'super_admin' as const,
  is_active: true,
  is_email_verified: true,
  created_at: '2024-01-15T08:00:00Z',
};

/** Standard token pair. */
export const MOCK_TOKENS = {
  access_token: 'mock_access_token_abc123',
  refresh_token: 'mock_refresh_token_xyz789',
  token_type: 'bearer',
  expires_in: 3600,
};

/** Mock server list for the dashboard. */
export const MOCK_SERVERS = [
  {
    id: 'srv_001',
    name: 'Frankfurt DE-1',
    location: 'Frankfurt, Germany',
    ip: '185.220.100.1',
    protocol: 'wireguard' as const,
    status: 'online' as const,
    load: 42,
    uptime: '99.98%',
    clients: 128,
  },
  {
    id: 'srv_002',
    name: 'Amsterdam NL-1',
    location: 'Amsterdam, Netherlands',
    ip: '45.32.150.2',
    protocol: 'vless' as const,
    status: 'online' as const,
    load: 67,
    uptime: '99.95%',
    clients: 256,
  },
  {
    id: 'srv_003',
    name: 'Tokyo JP-1',
    location: 'Tokyo, Japan',
    ip: '103.75.200.3',
    protocol: 'xhttp' as const,
    status: 'warning' as const,
    load: 89,
    uptime: '99.50%',
    clients: 312,
  },
  {
    id: 'srv_004',
    name: 'New York US-1',
    location: 'New York, USA',
    ip: '198.51.100.4',
    protocol: 'wireguard' as const,
    status: 'maintenance' as const,
    load: 0,
    uptime: '98.20%',
    clients: 0,
  },
  {
    id: 'srv_005',
    name: 'Singapore SG-1',
    location: 'Singapore',
    ip: '203.0.113.5',
    protocol: 'vless' as const,
    status: 'offline' as const,
    load: 0,
    uptime: '0%',
    clients: 0,
  },
];

/** Mock managed users for admin user-management panel. */
export const MOCK_MANAGED_USERS = [
  {
    id: 'usr_m_001',
    email: 'alice@example.com',
    plan: 'pro' as const,
    status: 'active' as const,
    dataUsage: 45.2,
    dataLimit: 100,
    expiresAt: '2026-06-01T00:00:00Z',
    lastActive: '2026-02-10T09:30:00Z',
  },
  {
    id: 'usr_m_002',
    email: 'bob@example.com',
    plan: 'basic' as const,
    status: 'expired' as const,
    dataUsage: 12.8,
    dataLimit: 50,
    expiresAt: '2025-12-15T00:00:00Z',
    lastActive: '2025-12-14T18:00:00Z',
  },
  {
    id: 'usr_m_003',
    email: 'charlie@example.com',
    plan: 'ultra' as const,
    status: 'active' as const,
    dataUsage: 210.5,
    dataLimit: 500,
    expiresAt: '2026-12-31T00:00:00Z',
    lastActive: '2026-02-09T22:15:00Z',
  },
  {
    id: 'usr_m_004',
    email: 'eve@example.com',
    plan: 'cyber' as const,
    status: 'banned' as const,
    dataUsage: 0,
    dataLimit: 1000,
    expiresAt: '2026-03-01T00:00:00Z',
    lastActive: '2026-01-20T14:00:00Z',
  },
];

// ---------------------------------------------------------------------------
// Auth Handlers
// ---------------------------------------------------------------------------

export const authHandlers = [
  /**
   * POST /auth/login
   * Accepts email + password, returns token pair.
   */
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as {
      email?: string;
      password?: string;
    };

    if (!body.email || !body.password) {
      return HttpResponse.json(
        { detail: 'Email and password are required' },
        { status: 422 },
      );
    }

    if (body.email === 'banned@cybervpn.io') {
      return HttpResponse.json(
        { detail: 'Account is disabled' },
        { status: 403 },
      );
    }

    if (body.password !== 'correct_password') {
      return HttpResponse.json(
        { detail: 'Invalid email or password' },
        { status: 401 },
      );
    }

    return HttpResponse.json(MOCK_TOKENS);
  }),

  /**
   * POST /auth/register
   * Creates a new user (is_active=false, is_email_verified=false).
   */
  http.post(`${API_BASE}/auth/register`, async ({ request }) => {
    const body = (await request.json()) as {
      login?: string;
      email?: string;
      password?: string;
    };

    if (!body.login || !body.email || !body.password) {
      return HttpResponse.json(
        { detail: 'All fields are required' },
        { status: 422 },
      );
    }

    if (body.email === 'taken@cybervpn.io') {
      return HttpResponse.json(
        { detail: 'Email already registered' },
        { status: 409 },
      );
    }

    return HttpResponse.json({
      id: 'usr_new_001',
      login: body.login,
      email: body.email,
      is_active: false,
      is_email_verified: false,
      message: 'Registration successful. Please verify your email.',
    });
  }),

  /**
   * POST /auth/verify-otp
   * Verifies the email OTP, activates user, returns tokens + user.
   */
  http.post(`${API_BASE}/auth/verify-otp`, async ({ request }) => {
    const body = (await request.json()) as {
      email?: string;
      code?: string;
    };

    if (body.code === '000000') {
      return HttpResponse.json(
        { detail: 'Invalid or expired OTP code', code: 'INVALID_OTP', attempts_remaining: 2 },
        { status: 400 },
      );
    }

    return HttpResponse.json({
      ...MOCK_TOKENS,
      user: MOCK_USER,
    });
  }),

  /**
   * POST /auth/resend-otp
   */
  http.post(`${API_BASE}/auth/resend-otp`, async () => {
    return HttpResponse.json({
      message: 'OTP sent successfully',
      resends_remaining: 2,
    });
  }),

  /**
   * POST /auth/logout
   */
  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' });
  }),

  /**
   * POST /auth/refresh
   * Returns new token pair.
   */
  http.post(`${API_BASE}/auth/refresh`, () => {
    return HttpResponse.json({
      ...MOCK_TOKENS,
      access_token: 'mock_refreshed_access_token',
      refresh_token: 'mock_refreshed_refresh_token',
    });
  }),

  /**
   * GET /auth/me
   * Returns the current authenticated user.
   */
  http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json(MOCK_USER);
  }),

  /**
   * DELETE /auth/me
   * Deletes the current user account.
   */
  http.delete(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json({ message: 'Account has been deleted' });
  }),

  /**
   * POST /auth/forgot-password
   * Always returns success to prevent email enumeration.
   */
  http.post(`${API_BASE}/auth/forgot-password`, async () => {
    return HttpResponse.json({
      message: 'If the email is registered, a reset code has been sent.',
    });
  }),

  /**
   * POST /auth/reset-password
   */
  http.post(`${API_BASE}/auth/reset-password`, async ({ request }) => {
    const body = (await request.json()) as {
      email?: string;
      code?: string;
      new_password?: string;
    };

    if (body.code === '000000') {
      return HttpResponse.json(
        { detail: 'Invalid or expired reset code' },
        { status: 400 },
      );
    }

    return HttpResponse.json({
      message: 'Password has been reset successfully.',
    });
  }),

  /**
   * POST /auth/magic-link
   */
  http.post(`${API_BASE}/auth/magic-link`, async () => {
    return HttpResponse.json({
      message: 'Magic link sent to your email.',
    });
  }),

  /**
   * POST /auth/magic-link/verify
   */
  http.post(`${API_BASE}/auth/magic-link/verify`, async ({ request }) => {
    const body = (await request.json()) as { token?: string };

    if (body.token === 'expired_token') {
      return HttpResponse.json(
        { detail: 'Token expired or invalid' },
        { status: 400 },
      );
    }

    return HttpResponse.json(MOCK_TOKENS);
  }),

  /**
   * POST /auth/oauth2/telegram/callback
   * Telegram Login Widget authentication.
   */
  http.post(`${API_BASE}/auth/oauth2/telegram/callback`, async ({ request }) => {
    const body = (await request.json()) as { id?: number; hash?: string };

    if (!body.id || !body.hash) {
      return HttpResponse.json(
        { detail: 'Missing required Telegram fields' },
        { status: 422 },
      );
    }

    if (body.hash === 'invalid_hash') {
      return HttpResponse.json(
        { detail: 'Invalid Telegram auth data' },
        { status: 401 },
      );
    }

    return HttpResponse.json({
      user: MOCK_USER,
      is_new_user: false,
    });
  }),

  /**
   * POST /auth/telegram/miniapp
   * Telegram Mini App initData authentication.
   */
  http.post(`${API_BASE}/auth/telegram/miniapp`, async ({ request }) => {
    const body = (await request.json()) as { init_data?: string };

    if (!body.init_data) {
      return HttpResponse.json(
        { detail: 'Missing init_data' },
        { status: 422 },
      );
    }

    if (body.init_data === 'invalid_init_data') {
      return HttpResponse.json(
        { detail: 'Invalid Telegram Mini App data' },
        { status: 401 },
      );
    }

    return HttpResponse.json({
      ...MOCK_TOKENS,
      user: {
        id: MOCK_USER.id,
        login: MOCK_USER.login,
        email: MOCK_USER.email,
        is_active: true,
        is_email_verified: true,
        created_at: MOCK_USER.created_at,
      },
      is_new_user: false,
    });
  }),

  /**
   * POST /auth/telegram/bot-link
   * Telegram bot deep-link token authentication.
   */
  http.post(`${API_BASE}/auth/telegram/bot-link`, async ({ request }) => {
    const body = (await request.json()) as { token?: string };

    if (!body.token) {
      return HttpResponse.json(
        { detail: 'Missing token' },
        { status: 422 },
      );
    }

    if (body.token === 'expired_bot_token') {
      return HttpResponse.json(
        { detail: 'Bot link token expired' },
        { status: 400 },
      );
    }

    return HttpResponse.json({
      ...MOCK_TOKENS,
      user: {
        id: MOCK_USER.id,
        login: MOCK_USER.login,
        email: MOCK_USER.email,
        is_active: true,
        is_email_verified: true,
        created_at: MOCK_USER.created_at,
      },
    });
  }),

  /**
   * GET /oauth/:provider/login
   * Get OAuth authorization URL for a provider.
   */
  http.get(`${API_BASE}/oauth/:provider/login`, ({ params, request }) => {
    const provider = params.provider as string;
    const validProviders = ['google', 'github', 'discord', 'apple', 'microsoft', 'twitter', 'telegram'];

    if (!validProviders.includes(provider)) {
      return HttpResponse.json(
        { detail: 'Unsupported OAuth provider' },
        { status: 400 },
      );
    }

    const url = new URL(request.url);
    const redirectUri = url.searchParams.get('redirect_uri');

    return HttpResponse.json({
      authorize_url: `https://${provider}.example.com/oauth/authorize?redirect_uri=${redirectUri}`,
      state: 'mock_csrf_state_token',
    });
  }),

  /**
   * POST /oauth/:provider/login/callback
   * Complete OAuth login callback.
   */
  http.post(`${API_BASE}/oauth/:provider/login/callback`, async ({ request }) => {
    const body = (await request.json()) as { code?: string; state?: string };

    if (!body.code || !body.state) {
      return HttpResponse.json(
        { detail: 'Missing code or state' },
        { status: 422 },
      );
    }

    if (body.code === 'invalid_code') {
      return HttpResponse.json(
        { detail: 'Invalid authorization code' },
        { status: 400 },
      );
    }

    return HttpResponse.json({
      ...MOCK_TOKENS,
      user: {
        id: MOCK_USER.id,
        login: MOCK_USER.login,
        email: MOCK_USER.email,
        is_active: true,
        is_email_verified: true,
        created_at: MOCK_USER.created_at,
      },
      is_new_user: false,
      requires_2fa: false,
      tfa_token: null,
    });
  }),

  /**
   * GET /oauth/telegram/authorize
   * Get Telegram OAuth authorize URL for account linking (authenticated).
   */
  http.get(`${API_BASE}/oauth/telegram/authorize`, ({ request }) => {
    const url = new URL(request.url);
    const redirectUri = url.searchParams.get('redirect_uri');

    return HttpResponse.json({
      authorize_url: `https://telegram.example.com/oauth/authorize?redirect_uri=${redirectUri}`,
      state: 'mock_link_state_token',
    });
  }),

  /**
   * POST /oauth/telegram/callback
   * Link Telegram account via OAuth callback (authenticated).
   */
  http.post(`${API_BASE}/oauth/telegram/callback`, async ({ request }) => {
    const body = (await request.json()) as { hash?: string; state?: string };

    if (!body.hash || !body.state) {
      return HttpResponse.json(
        { detail: 'Missing required fields' },
        { status: 422 },
      );
    }

    return HttpResponse.json({
      status: 'linked',
      provider: 'telegram',
      provider_user_id: '987654321',
    });
  }),

  /**
   * DELETE /oauth/:provider
   * Unlink an OAuth provider from the current user (authenticated).
   */
  http.delete(`${API_BASE}/oauth/:provider`, ({ params }) => {
    const provider = params.provider as string;
    const validProviders = ['google', 'github', 'discord', 'apple', 'microsoft', 'twitter', 'telegram'];

    if (!validProviders.includes(provider)) {
      return HttpResponse.json(
        { detail: 'Unsupported OAuth provider' },
        { status: 400 },
      );
    }

    return HttpResponse.json({
      status: 'unlinked',
      provider,
    });
  }),
];

// ---------------------------------------------------------------------------
// Server Handlers
// ---------------------------------------------------------------------------

export const serverHandlers = [
  /**
   * GET /servers
   * Returns the list of VPN servers.
   */
  http.get(`${API_BASE}/servers`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const protocol = url.searchParams.get('protocol');

    let filtered = [...MOCK_SERVERS];

    if (status) {
      filtered = filtered.filter((s) => s.status === status);
    }
    if (protocol) {
      filtered = filtered.filter((s) => s.protocol === protocol);
    }

    return HttpResponse.json(filtered);
  }),

  /**
   * GET /servers/:id
   * Returns a single server by ID.
   */
  http.get(`${API_BASE}/servers/:id`, ({ params }) => {
    const server = MOCK_SERVERS.find((s) => s.id === params.id);

    if (!server) {
      return HttpResponse.json(
        { detail: 'Server not found' },
        { status: 404 },
      );
    }

    return HttpResponse.json(server);
  }),
];

// ---------------------------------------------------------------------------
// User Management Handlers (admin panel)
// ---------------------------------------------------------------------------

export const userManagementHandlers = [
  /**
   * GET /users
   * Returns all managed users (admin endpoint).
   */
  http.get(`${API_BASE}/users`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const plan = url.searchParams.get('plan');
    const page = parseInt(url.searchParams.get('page') || '1', 10);
    const limit = parseInt(url.searchParams.get('limit') || '20', 10);

    let filtered = [...MOCK_MANAGED_USERS];

    if (status) {
      filtered = filtered.filter((u) => u.status === status);
    }
    if (plan) {
      filtered = filtered.filter((u) => u.plan === plan);
    }

    const start = (page - 1) * limit;
    const paginated = filtered.slice(start, start + limit);

    return HttpResponse.json({
      items: paginated,
      total: filtered.length,
      page,
      limit,
    });
  }),

  /**
   * GET /users/:id
   * Returns a single managed user by ID.
   */
  http.get(`${API_BASE}/users/:id`, ({ params }) => {
    const user = MOCK_MANAGED_USERS.find((u) => u.id === params.id);

    if (!user) {
      return HttpResponse.json(
        { detail: 'User not found' },
        { status: 404 },
      );
    }

    return HttpResponse.json(user);
  }),

  /**
   * PATCH /users/:id
   * Update a managed user (admin action).
   */
  http.patch(`${API_BASE}/users/:id`, async ({ params, request }) => {
    const user = MOCK_MANAGED_USERS.find((u) => u.id === params.id);

    if (!user) {
      return HttpResponse.json(
        { detail: 'User not found' },
        { status: 404 },
      );
    }

    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...user, ...body });
  }),

  /**
   * DELETE /users/:id
   * Delete a managed user (admin action).
   */
  http.delete(`${API_BASE}/users/:id`, ({ params }) => {
    const user = MOCK_MANAGED_USERS.find((u) => u.id === params.id);

    if (!user) {
      return HttpResponse.json(
        { detail: 'User not found' },
        { status: 404 },
      );
    }

    return HttpResponse.json({ message: 'User deleted successfully' });
  }),
];

// ---------------------------------------------------------------------------
// Combined Handlers (default export for MSW server setup)
// ---------------------------------------------------------------------------

export const handlers = [
  ...authHandlers,
  ...serverHandlers,
  ...userManagementHandlers,
];
