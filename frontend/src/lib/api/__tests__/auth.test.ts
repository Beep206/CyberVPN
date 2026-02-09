/**
 * QUAL-02.3 -- Auth API Client Unit Tests
 *
 * Tests the authApi methods from src/lib/api/auth.ts by exercising the real
 * axios-based apiClient against MSW mock handlers. Each test follows
 * Arrange-Act-Assert and is fully independent.
 *
 * MSW handlers are defined in src/test/mocks/handlers.ts and started/stopped
 * by the global test setup in src/test/setup.ts.
 *
 * NOTE: The apiClient response interceptor converts 401 responses (except on
 * /auth/me) into a token-refresh flow. When no refresh token is stored the
 * interceptor throws Error('No refresh token') and redirects window.location.
 * Tests must reset window.location.href after each test to prevent subsequent
 * requests from failing with "Invalid URL".
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { MOCK_USER, MOCK_TOKENS } from '@/test/mocks/handlers';
import { authApi } from '../auth';
import { tokenStorage } from '../client';
import { AxiosError } from 'axios';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = 'http://localhost:8000/api/v1';

/** Type guard for AxiosError to safely inspect response data in catch blocks. */
function isAxiosError(error: unknown): error is AxiosError<{ detail: string }> {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as Record<string, unknown>).isAxiosError === true
  );
}

// ---------------------------------------------------------------------------
// Global setup / teardown for every test
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();
  // Ensure window.location is reset to a valid absolute URL so axios can
  // resolve its baseURL properly (the 401 interceptor mutates location.href).
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  // Safety net: always restore location after each test
  window.location.href = 'http://localhost:3000';
});

// ===========================================================================
// authApi.login
// ===========================================================================

describe('authApi.login', () => {
  it('test_login_success_returns_token_response', async () => {
    // Arrange
    const credentials = { email: 'testuser@cybervpn.io', password: 'correct_password' };

    // Act
    const response = await authApi.login(credentials);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe(MOCK_TOKENS.access_token);
    expect(response.data.refresh_token).toBe(MOCK_TOKENS.refresh_token);
    expect(response.data.token_type).toBe('bearer');
    expect(response.data.expires_in).toBe(3600);
  });

  it('test_login_invalid_credentials_rejects_with_error', async () => {
    // Arrange
    // The MSW handler returns 401 for wrong password. The apiClient 401
    // interceptor then tries to refresh but finds no refresh token in
    // localStorage and throws Error('No refresh token').
    const credentials = { email: 'testuser@cybervpn.io', password: 'wrong_password' };

    // Act & Assert
    await expect(authApi.login(credentials)).rejects.toThrow('No refresh token');
  });

  it('test_login_invalid_credentials_with_refresh_token_retries_and_gets_401', async () => {
    // Arrange -- provide a refresh token so the interceptor tries to refresh.
    // The refresh succeeds (MSW default), then it retries the login,
    // but the login still returns 401 because the credentials are wrong.
    // The _retry flag prevents infinite loops -- the retried 401 passes through.
    tokenStorage.setTokens('old_access', 'some_refresh_token');
    const credentials = { email: 'testuser@cybervpn.io', password: 'wrong_password' };

    // Act & Assert
    try {
      await authApi.login(credentials);
      expect.fail('Expected request to reject');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
        expect(error.response?.data.detail).toBe('Invalid email or password');
      }
    }
  });

  it('test_login_banned_account_rejects_with_403', async () => {
    // Arrange -- 403 passes through the interceptor without modification
    const credentials = { email: 'banned@cybervpn.io', password: 'correct_password' };

    // Act & Assert
    try {
      await authApi.login(credentials);
      expect.fail('Expected request to reject with 403');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(403);
        expect(error.response?.data.detail).toBe('Account is disabled');
      }
    }
  });

  it('test_login_missing_fields_rejects_with_422', async () => {
    // Arrange -- handler returns 422 when fields are missing/empty
    const credentials = { email: '', password: '' };

    // Act & Assert
    try {
      await authApi.login(credentials);
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_login_sends_remember_me_field', async () => {
    // Arrange -- override handler to capture the request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/auth/login`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(MOCK_TOKENS);
      }),
    );

    // Act
    await authApi.login({
      email: 'user@cybervpn.io',
      password: 'correct_password',
      remember_me: true,
    });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.remember_me).toBe(true);
  });
});

// ===========================================================================
// authApi.register
// ===========================================================================

describe('authApi.register', () => {
  it('test_register_success_returns_unverified_user', async () => {
    // Arrange
    const data = { login: 'newuser', email: 'new@cybervpn.io', password: 'S3cure!Pass' };

    // Act
    const response = await authApi.register(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.id).toBe('usr_new_001');
    expect(response.data.login).toBe('newuser');
    expect(response.data.email).toBe('new@cybervpn.io');
    expect(response.data.is_active).toBe(false);
    expect(response.data.is_email_verified).toBe(false);
    expect(response.data.message).toContain('verify');
  });

  it('test_register_duplicate_email_rejects_with_409', async () => {
    // Arrange
    const data = { login: 'taken', email: 'taken@cybervpn.io', password: 'AnyPass1!' };

    // Act & Assert
    try {
      await authApi.register(data);
      expect.fail('Expected request to reject with 409');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(409);
        expect(error.response?.data.detail).toBe('Email already registered');
      }
    }
  });

  it('test_register_missing_fields_rejects_with_422', async () => {
    // Arrange -- empty login triggers 422
    const data = { login: '', email: 'x@y.com', password: 'abc123' };

    // Act & Assert
    try {
      await authApi.register(data);
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });
});

// ===========================================================================
// authApi.verifyOtp
// ===========================================================================

describe('authApi.verifyOtp', () => {
  it('test_verify_otp_success_returns_tokens_and_user', async () => {
    // Arrange
    const data = { email: 'testuser@cybervpn.io', code: '123456' };

    // Act
    const response = await authApi.verifyOtp(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe(MOCK_TOKENS.access_token);
    expect(response.data.refresh_token).toBe(MOCK_TOKENS.refresh_token);
    expect(response.data.user.id).toBe(MOCK_USER.id);
    expect(response.data.user.email).toBe(MOCK_USER.email);
  });

  it('test_verify_otp_invalid_code_rejects_with_400', async () => {
    // Arrange -- code 000000 triggers invalid OTP in the handler
    const data = { email: 'testuser@cybervpn.io', code: '000000' };

    // Act & Assert
    try {
      await authApi.verifyOtp(data);
      expect.fail('Expected request to reject with 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Invalid or expired OTP code');
      }
    }
  });
});

// ===========================================================================
// authApi.resendOtp
// ===========================================================================

describe('authApi.resendOtp', () => {
  it('test_resend_otp_success_returns_message_and_remaining', async () => {
    // Arrange
    const data = { email: 'testuser@cybervpn.io' };

    // Act
    const response = await authApi.resendOtp(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('OTP sent successfully');
    expect(response.data.resends_remaining).toBe(2);
  });

  it('test_resend_otp_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange -- override handler to return 429
    server.use(
      http.post(`${API_BASE}/auth/resend-otp`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '60' } },
        );
      }),
    );

    // Act & Assert -- the interceptor converts 429 to RateLimitError
    try {
      await authApi.resendOtp({ email: 'testuser@cybervpn.io' });
      expect.fail('Expected request to reject');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(60);
    }
  });
});

// ===========================================================================
// authApi.forgotPassword
// ===========================================================================

describe('authApi.forgotPassword', () => {
  it('test_forgot_password_registered_email_succeeds', async () => {
    // Arrange
    const data = { email: 'testuser@cybervpn.io' };

    // Act
    const response = await authApi.forgotPassword(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBeDefined();
    expect(response.data.message).toContain('reset code');
  });

  it('test_forgot_password_unknown_email_still_succeeds_anti_enumeration', async () => {
    // Arrange -- even a nonexistent email returns 200 (anti-enumeration)
    const data = { email: 'nobody@doesnotexist.com' };

    // Act
    const response = await authApi.forgotPassword(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBeDefined();
  });

  it('test_forgot_password_empty_email_still_succeeds', async () => {
    // The handler always returns success regardless of input
    const data = { email: '' };

    // Act
    const response = await authApi.forgotPassword(data);

    // Assert
    expect(response.status).toBe(200);
  });
});

// ===========================================================================
// authApi.resetPassword
// ===========================================================================

describe('authApi.resetPassword', () => {
  it('test_reset_password_success_with_valid_code', async () => {
    // Arrange
    const data = {
      email: 'testuser@cybervpn.io',
      code: '123456',
      new_password: 'NewS3cure!Pass',
    };

    // Act
    const response = await authApi.resetPassword(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toContain('reset');
  });

  it('test_reset_password_invalid_code_rejects_with_400', async () => {
    // Arrange -- code 000000 triggers invalid response in handler
    const data = {
      email: 'testuser@cybervpn.io',
      code: '000000',
      new_password: 'NewPass1!',
    };

    // Act & Assert
    try {
      await authApi.resetPassword(data);
      expect.fail('Expected request to reject with 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Invalid or expired reset code');
      }
    }
  });
});

// ===========================================================================
// authApi.deleteAccount
// ===========================================================================

describe('authApi.deleteAccount', () => {
  it('test_delete_account_success_returns_confirmation_message', async () => {
    // Act
    const response = await authApi.deleteAccount();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Account has been deleted');
  });

  it('test_delete_account_unauthenticated_rejects_with_401', async () => {
    // Arrange -- override the DELETE /auth/me to return 401.
    // The URL includes /auth/me, so the interceptor passes through without refresh.
    server.use(
      http.delete(`${API_BASE}/auth/me`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.deleteAccount();
      expect.fail('Expected request to reject with 401');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });
});

// ===========================================================================
// authApi.refresh
// ===========================================================================

describe('authApi.refresh', () => {
  it('test_refresh_success_returns_new_tokens', async () => {
    // Act
    const response = await authApi.refresh();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe('mock_refreshed_access_token');
    expect(response.data.refresh_token).toBe('mock_refreshed_refresh_token');
    expect(response.data.token_type).toBe('bearer');
  });

  it('test_refresh_expired_token_rejects', async () => {
    // Arrange -- override handler to simulate expired refresh token
    server.use(
      http.post(`${API_BASE}/auth/refresh`, () => {
        return HttpResponse.json(
          { detail: 'Refresh token expired' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert -- the 401 interceptor will try to refresh using this
    // same endpoint which also 401s, leading to 'No refresh token' error
    await expect(authApi.refresh()).rejects.toBeDefined();
  });
});

// ===========================================================================
// authApi.me
// ===========================================================================

describe('authApi.me', () => {
  it('test_get_me_success_returns_user_profile', async () => {
    // Act
    const response = await authApi.me();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.id).toBe(MOCK_USER.id);
    expect(response.data.email).toBe(MOCK_USER.email);
    expect(response.data.login).toBe(MOCK_USER.login);
    expect(response.data.role).toBe('user');
    expect(response.data.is_active).toBe(true);
    expect(response.data.is_email_verified).toBe(true);
    expect(response.data.created_at).toBe('2025-06-01T12:00:00Z');
  });

  it('test_get_me_unauthenticated_rejects_with_401', async () => {
    // Arrange -- the interceptor has a special case: /auth/me 401s pass through
    server.use(
      http.get(`${API_BASE}/auth/me`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.me();
      expect.fail('Expected request to reject with 401');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
        expect(error.response?.data.detail).toBe('Not authenticated');
      }
    }
  });
});

// ===========================================================================
// authApi.logout
// ===========================================================================

describe('authApi.logout', () => {
  it('test_logout_success_returns_message', async () => {
    // Act
    const response = await authApi.logout();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Logged out successfully');
  });
});

// ===========================================================================
// authApi.requestMagicLink
// ===========================================================================

describe('authApi.requestMagicLink', () => {
  it('test_request_magic_link_success_returns_message', async () => {
    // Arrange
    const data = { email: 'user@cybervpn.io' };

    // Act
    const response = await authApi.requestMagicLink(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Magic link sent to your email.');
  });
});

// ===========================================================================
// authApi.verifyMagicLink
// ===========================================================================

describe('authApi.verifyMagicLink', () => {
  it('test_verify_magic_link_success_returns_tokens', async () => {
    // Arrange
    const data = { token: 'valid_token_abc123' };

    // Act
    const response = await authApi.verifyMagicLink(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe(MOCK_TOKENS.access_token);
    expect(response.data.refresh_token).toBe(MOCK_TOKENS.refresh_token);
    expect(response.data.token_type).toBe('bearer');
  });

  it('test_verify_magic_link_expired_token_rejects_with_400', async () => {
    // Arrange -- 'expired_token' triggers 400 in the handler
    const data = { token: 'expired_token' };

    // Act & Assert
    try {
      await authApi.verifyMagicLink(data);
      expect.fail('Expected request to reject with 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Token expired or invalid');
      }
    }
  });
});

// ===========================================================================
// Authorization header injection (request interceptor)
// ===========================================================================

describe('authApi request interceptor', () => {
  it('test_request_includes_authorization_header_when_token_stored', async () => {
    // Arrange -- store a token so the interceptor injects it
    localStorage.setItem('access_token', 'my_jwt_token');

    let capturedAuthHeader: string | undefined;
    server.use(
      http.get(`${API_BASE}/auth/me`, ({ request }) => {
        capturedAuthHeader = request.headers.get('Authorization') ?? undefined;
        return HttpResponse.json(MOCK_USER);
      }),
    );

    // Act
    await authApi.me();

    // Assert
    expect(capturedAuthHeader).toBe('Bearer my_jwt_token');
  });

  it('test_request_omits_authorization_header_when_no_token', async () => {
    // Arrange -- localStorage is cleared in beforeEach
    let capturedAuthHeader: string | null = null;
    server.use(
      http.get(`${API_BASE}/auth/me`, ({ request }) => {
        capturedAuthHeader = request.headers.get('Authorization');
        return HttpResponse.json(MOCK_USER);
      }),
    );

    // Act
    await authApi.me();

    // Assert -- no token means no Authorization header
    expect(capturedAuthHeader).toBeNull();
  });
});

// ===========================================================================
// Server error and network error handling
// ===========================================================================

describe('authApi error handling', () => {
  it('test_server_error_500_rejects_with_axios_error', async () => {
    // Arrange -- 500 passes through the interceptor unmodified
    server.use(
      http.post(`${API_BASE}/auth/login`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.login({ email: 'user@test.com', password: 'pass' });
      expect.fail('Expected request to reject with 500');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });

  it('test_network_error_rejects', async () => {
    // Arrange -- simulate a network failure
    server.use(
      http.post(`${API_BASE}/auth/login`, () => {
        return HttpResponse.error();
      }),
    );

    // Act & Assert
    await expect(
      authApi.login({ email: 'user@test.com', password: 'pass' }),
    ).rejects.toBeDefined();
  });

  it('test_rate_limit_429_converts_to_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/login`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '30' } },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.login({ email: 'x@y.com', password: 'z' });
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(30);
      expect((error as Error).message).toContain('30 seconds');
    }
  });
});

// ===========================================================================
// 401 interceptor behavior (token refresh flow)
// ===========================================================================

describe('apiClient 401 interceptor', () => {
  it('test_401_on_auth_me_passes_through_without_refresh', async () => {
    // Arrange -- /auth/me is special-cased: 401 is not retried
    server.use(
      http.get(`${API_BASE}/auth/me`, () => {
        return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
      }),
    );

    // Act & Assert
    try {
      await authApi.me();
      expect.fail('Expected 401');
    } catch (error: unknown) {
      // Should be the original AxiosError, not transformed
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });

  it('test_401_without_refresh_token_throws_no_refresh_token', async () => {
    // Arrange -- no refresh token in localStorage; call a non-/auth/me endpoint
    server.use(
      http.post(`${API_BASE}/auth/logout`, () => {
        return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
      }),
    );

    // Act & Assert -- interceptor finds no refresh token
    await expect(authApi.logout()).rejects.toThrow('No refresh token');
  });

  it('test_401_with_refresh_token_retries_original_request', async () => {
    // Arrange -- store a refresh token so the interceptor can refresh
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.post(`${API_BASE}/auth/logout`, () => {
        callCount += 1;
        if (callCount === 1) {
          // First call: 401 to trigger refresh
          return HttpResponse.json({ detail: 'Token expired' }, { status: 401 });
        }
        // Second call (after refresh): success
        return HttpResponse.json({ message: 'Logged out successfully' });
      }),
    );

    // Act
    const response = await authApi.logout();

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Logged out successfully');
    // The interceptor should have stored the new tokens from the refresh
    expect(tokenStorage.getAccessToken()).toBe('mock_refreshed_access_token');
    expect(tokenStorage.getRefreshToken()).toBe('mock_refreshed_refresh_token');
  });
});

// ===========================================================================
// authApi.telegramWidget
// ===========================================================================

describe('authApi.telegramWidget', () => {
  it('test_telegram_widget_success_returns_auth_response', async () => {
    // Arrange
    const data = {
      id: 123456,
      first_name: 'Test',
      last_name: 'User',
      username: 'testuser',
      photo_url: 'https://t.me/i/photo.jpg',
      auth_date: 1700000000,
      hash: 'valid_hash_abc123',
    };

    // Act
    const response = await authApi.telegramWidget(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.user.id).toBe(MOCK_USER.id);
    expect(response.data.user.email).toBe(MOCK_USER.email);
    expect(response.data.is_new_user).toBe(false);
  });

  it('test_telegram_widget_invalid_hash_rejects', async () => {
    // Arrange -- 'invalid_hash' triggers 401 in the handler. The 401
    // interceptor then tries to refresh but finds no refresh token.
    const data = {
      id: 123456,
      first_name: 'Test',
      auth_date: 1700000000,
      hash: 'invalid_hash',
    };

    // Act & Assert
    await expect(authApi.telegramWidget(data)).rejects.toThrow('No refresh token');
  });

  it('test_telegram_widget_invalid_hash_with_refresh_token_gets_401', async () => {
    // Arrange -- provide a refresh token so the interceptor retries.
    // The retry still gets 401 because the hash is invalid.
    tokenStorage.setTokens('old_access', 'some_refresh_token');
    const data = {
      id: 123456,
      first_name: 'Test',
      auth_date: 1700000000,
      hash: 'invalid_hash',
    };

    // Act & Assert
    try {
      await authApi.telegramWidget(data);
      expect.fail('Expected request to reject');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
        expect(error.response?.data.detail).toBe('Invalid Telegram auth data');
      }
    }
  });

  it('test_telegram_widget_sends_all_fields_in_request_body', async () => {
    // Arrange -- override handler to capture the full request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/auth/oauth2/telegram/callback`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ user: MOCK_USER, is_new_user: false });
      }),
    );

    const data = {
      id: 999,
      first_name: 'Alice',
      last_name: 'Smith',
      username: 'alice_smith',
      photo_url: 'https://t.me/photo.jpg',
      auth_date: 1700000001,
      hash: 'abc123def456',
    };

    // Act
    await authApi.telegramWidget(data);

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.id).toBe(999);
    expect(capturedBody!.first_name).toBe('Alice');
    expect(capturedBody!.last_name).toBe('Smith');
    expect(capturedBody!.username).toBe('alice_smith');
    expect(capturedBody!.photo_url).toBe('https://t.me/photo.jpg');
    expect(capturedBody!.auth_date).toBe(1700000001);
    expect(capturedBody!.hash).toBe('abc123def456');
  });

  it('test_telegram_widget_optional_fields_can_be_omitted', async () => {
    // Arrange -- only required fields
    const data = {
      id: 123456,
      first_name: 'Test',
      auth_date: 1700000000,
      hash: 'valid_hash',
    };

    // Act
    const response = await authApi.telegramWidget(data);

    // Assert
    expect(response.status).toBe(200);
  });

  it('test_telegram_widget_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/oauth2/telegram/callback`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    const data = {
      id: 123456,
      first_name: 'Test',
      auth_date: 1700000000,
      hash: 'valid_hash',
    };

    // Act & Assert
    try {
      await authApi.telegramWidget(data);
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});

// ===========================================================================
// authApi.telegramMiniApp
// ===========================================================================

describe('authApi.telegramMiniApp', () => {
  it('test_telegram_miniapp_success_returns_tokens_and_user', async () => {
    // Arrange
    const initData = 'valid_init_data_string';

    // Act
    const response = await authApi.telegramMiniApp(initData);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe(MOCK_TOKENS.access_token);
    expect(response.data.refresh_token).toBe(MOCK_TOKENS.refresh_token);
    expect(response.data.user.id).toBe(MOCK_USER.id);
    expect(response.data.is_new_user).toBe(false);
  });

  it('test_telegram_miniapp_sends_init_data_in_body', async () => {
    // Arrange -- capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/auth/telegram/miniapp`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...MOCK_TOKENS,
          user: { id: 'u1', login: 'x', email: null, is_active: true, is_email_verified: false, created_at: '' },
          is_new_user: false,
        });
      }),
    );

    // Act
    await authApi.telegramMiniApp('my_init_data_abc');

    // Assert -- the method wraps initData as { init_data: ... }
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.init_data).toBe('my_init_data_abc');
  });

  it('test_telegram_miniapp_invalid_data_rejects', async () => {
    // Arrange -- 'invalid_init_data' triggers 401 in the handler.
    // The 401 interceptor tries to refresh but finds no refresh token.
    await expect(authApi.telegramMiniApp('invalid_init_data')).rejects.toThrow('No refresh token');
  });

  it('test_telegram_miniapp_empty_string_rejects_with_422', async () => {
    // Arrange -- empty init_data triggers 422 in handler
    try {
      await authApi.telegramMiniApp('');
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_telegram_miniapp_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/telegram/miniapp`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '120' } },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.telegramMiniApp('some_data');
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(120);
    }
  });
});

// ===========================================================================
// authApi.telegramBotLink
// ===========================================================================

describe('authApi.telegramBotLink', () => {
  it('test_telegram_bot_link_success_returns_tokens_and_user', async () => {
    // Arrange
    const data = { token: 'valid_bot_link_token' };

    // Act
    const response = await authApi.telegramBotLink(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe(MOCK_TOKENS.access_token);
    expect(response.data.refresh_token).toBe(MOCK_TOKENS.refresh_token);
    expect(response.data.user.id).toBe(MOCK_USER.id);
    expect(response.data.user.login).toBe(MOCK_USER.login);
  });

  it('test_telegram_bot_link_expired_token_rejects_with_400', async () => {
    // Arrange -- 'expired_bot_token' triggers 400 in handler
    const data = { token: 'expired_bot_token' };

    // Act & Assert
    try {
      await authApi.telegramBotLink(data);
      expect.fail('Expected request to reject with 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Bot link token expired');
      }
    }
  });

  it('test_telegram_bot_link_sends_token_in_body', async () => {
    // Arrange
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/auth/telegram/bot-link`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...MOCK_TOKENS,
          user: { id: 'u1', login: 'x', email: null, is_active: true, is_email_verified: false, created_at: '' },
        });
      }),
    );

    // Act
    await authApi.telegramBotLink({ token: 'my_bot_token_xyz' });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.token).toBe('my_bot_token_xyz');
  });

  it('test_telegram_bot_link_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/telegram/bot-link`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.telegramBotLink({ token: 'any_token' });
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});

// ===========================================================================
// authApi.oauthLoginAuthorize
// ===========================================================================

describe('authApi.oauthLoginAuthorize', () => {
  it('test_oauth_login_authorize_success_returns_authorize_url_and_state', async () => {
    // Arrange
    const provider = 'google' as const;
    const redirectUri = 'https://cybervpn.io/oauth/callback';

    // Act
    const response = await authApi.oauthLoginAuthorize(provider, redirectUri);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.authorize_url).toContain('google.example.com');
    expect(response.data.authorize_url).toContain(redirectUri);
    expect(response.data.state).toBe('mock_csrf_state_token');
  });

  it('test_oauth_login_authorize_different_providers', async () => {
    // Arrange -- test with github
    const response = await authApi.oauthLoginAuthorize('github', 'https://app.cybervpn.io/callback');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.authorize_url).toContain('github.example.com');
    expect(response.data.state).toBeDefined();
  });

  it('test_oauth_login_authorize_passes_redirect_uri_as_query_param', async () => {
    // Arrange -- capture request URL
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/oauth/:provider/login`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          authorize_url: 'https://example.com/auth',
          state: 'state_tok',
        });
      }),
    );

    // Act
    await authApi.oauthLoginAuthorize('discord', 'https://myapp.com/cb');

    // Assert
    const url = new URL(capturedUrl);
    expect(url.searchParams.get('redirect_uri')).toBe('https://myapp.com/cb');
  });

  it('test_oauth_login_authorize_unsupported_provider_rejects_with_400', async () => {
    // Arrange -- cast an invalid provider name to satisfy TS
    try {
      await authApi.oauthLoginAuthorize('unsupported_provider' as 'google', 'https://app.com/cb');
      expect.fail('Expected request to reject with 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Unsupported OAuth provider');
      }
    }
  });

  it('test_oauth_login_authorize_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/oauth/:provider/login`, () => {
        return HttpResponse.json(
          { detail: 'OAuth service unavailable' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.oauthLoginAuthorize('google', 'https://app.com/cb');
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});

// ===========================================================================
// authApi.oauthLoginCallback
// ===========================================================================

describe('authApi.oauthLoginCallback', () => {
  it('test_oauth_login_callback_success_returns_tokens_and_user', async () => {
    // Arrange
    const data = {
      code: 'valid_auth_code',
      state: 'mock_csrf_state',
      redirect_uri: 'https://cybervpn.io/callback',
    };

    // Act
    const response = await authApi.oauthLoginCallback('google', data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.access_token).toBe(MOCK_TOKENS.access_token);
    expect(response.data.refresh_token).toBe(MOCK_TOKENS.refresh_token);
    expect(response.data.user.id).toBe(MOCK_USER.id);
    expect(response.data.is_new_user).toBe(false);
    expect(response.data.requires_2fa).toBe(false);
    expect(response.data.tfa_token).toBeNull();
  });

  it('test_oauth_login_callback_invalid_code_rejects_with_400', async () => {
    // Arrange -- 'invalid_code' triggers 400 in handler
    const data = {
      code: 'invalid_code',
      state: 'mock_csrf_state',
      redirect_uri: 'https://cybervpn.io/callback',
    };

    // Act & Assert
    try {
      await authApi.oauthLoginCallback('google', data);
      expect.fail('Expected request to reject with 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Invalid authorization code');
      }
    }
  });

  it('test_oauth_login_callback_sends_correct_body', async () => {
    // Arrange -- capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/oauth/:provider/login/callback`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...MOCK_TOKENS,
          user: { id: 'u1', login: 'x', email: null, is_active: true, is_email_verified: false, created_at: '' },
          is_new_user: false,
          requires_2fa: false,
          tfa_token: null,
        });
      }),
    );

    const data = {
      code: 'auth_code_123',
      state: 'csrf_state_456',
      redirect_uri: 'https://app.cybervpn.io/cb',
    };

    // Act
    await authApi.oauthLoginCallback('github', data);

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.code).toBe('auth_code_123');
    expect(capturedBody!.state).toBe('csrf_state_456');
    expect(capturedBody!.redirect_uri).toBe('https://app.cybervpn.io/cb');
  });

  it('test_oauth_login_callback_with_2fa_required', async () => {
    // Arrange -- override to return requires_2fa: true
    server.use(
      http.post(`${API_BASE}/oauth/:provider/login/callback`, async () => {
        return HttpResponse.json({
          ...MOCK_TOKENS,
          user: { id: 'u1', login: 'x', email: null, is_active: true, is_email_verified: true, created_at: '' },
          is_new_user: false,
          requires_2fa: true,
          tfa_token: '2fa_token_abc',
        });
      }),
    );

    const data = {
      code: 'valid_code',
      state: 'valid_state',
      redirect_uri: 'https://cybervpn.io/cb',
    };

    // Act
    const response = await authApi.oauthLoginCallback('google', data);

    // Assert
    expect(response.data.requires_2fa).toBe(true);
    expect(response.data.tfa_token).toBe('2fa_token_abc');
  });

  it('test_oauth_login_callback_new_user_flag', async () => {
    // Arrange -- override to return is_new_user: true
    server.use(
      http.post(`${API_BASE}/oauth/:provider/login/callback`, async () => {
        return HttpResponse.json({
          ...MOCK_TOKENS,
          user: { id: 'u2', login: 'newbie', email: 'new@test.com', is_active: true, is_email_verified: true, created_at: '' },
          is_new_user: true,
          requires_2fa: false,
          tfa_token: null,
        });
      }),
    );

    const data = {
      code: 'new_user_code',
      state: 'state',
      redirect_uri: 'https://cybervpn.io/cb',
    };

    // Act
    const response = await authApi.oauthLoginCallback('github', data);

    // Assert
    expect(response.data.is_new_user).toBe(true);
    expect(response.data.user.login).toBe('newbie');
  });

  it('test_oauth_login_callback_missing_code_rejects_with_422', async () => {
    // Arrange -- missing code field
    const data = {
      code: '',
      state: 'some_state',
      redirect_uri: 'https://cybervpn.io/cb',
    };

    // Act & Assert
    try {
      await authApi.oauthLoginCallback('google', data);
      expect.fail('Expected request to reject with 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });
});

// ===========================================================================
// authApi.telegramLinkAuthorize
// ===========================================================================

describe('authApi.telegramLinkAuthorize', () => {
  it('test_telegram_link_authorize_success_returns_url_and_state', async () => {
    // Arrange
    const redirectUri = 'https://cybervpn.io/profile/link';

    // Act
    const response = await authApi.telegramLinkAuthorize(redirectUri);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.authorize_url).toContain('telegram.example.com');
    expect(response.data.authorize_url).toContain(redirectUri);
    expect(response.data.state).toBe('mock_link_state_token');
  });

  it('test_telegram_link_authorize_passes_redirect_uri_param', async () => {
    // Arrange -- capture request URL
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/oauth/telegram/authorize`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          authorize_url: 'https://tg.example.com/auth',
          state: 'link_state',
        });
      }),
    );

    // Act
    await authApi.telegramLinkAuthorize('https://myapp.com/link-callback');

    // Assert
    const url = new URL(capturedUrl);
    expect(url.searchParams.get('redirect_uri')).toBe('https://myapp.com/link-callback');
  });

  it('test_telegram_link_authorize_unauthenticated_rejects_with_401', async () => {
    // Arrange -- override to return 401 (this is an authenticated endpoint)
    server.use(
      http.get(`${API_BASE}/oauth/telegram/authorize`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert -- the 401 interceptor will try to refresh, fail with no token
    await expect(
      authApi.telegramLinkAuthorize('https://cybervpn.io/link'),
    ).rejects.toThrow('No refresh token');
  });

  it('test_telegram_link_authorize_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/oauth/telegram/authorize`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.telegramLinkAuthorize('https://cybervpn.io/link');
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});

// ===========================================================================
// authApi.telegramLinkCallback
// ===========================================================================

describe('authApi.telegramLinkCallback', () => {
  it('test_telegram_link_callback_success_returns_linked_status', async () => {
    // Arrange
    const data = {
      id: 987654,
      first_name: 'Linked',
      auth_date: 1700000000,
      hash: 'valid_link_hash',
      state: 'mock_link_state_token',
    };

    // Act
    const response = await authApi.telegramLinkCallback(data);

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('linked');
    expect(response.data.provider).toBe('telegram');
    expect(response.data.provider_user_id).toBe('987654321');
  });

  it('test_telegram_link_callback_sends_all_fields_in_body', async () => {
    // Arrange -- capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/oauth/telegram/callback`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ status: 'linked', provider: 'telegram' });
      }),
    );

    const data = {
      id: 111,
      first_name: 'Bob',
      last_name: 'Jones',
      username: 'bobjones',
      photo_url: 'https://t.me/bob.jpg',
      auth_date: 1700000002,
      hash: 'hash_abc',
      state: 'link_state_xyz',
    };

    // Act
    await authApi.telegramLinkCallback(data);

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.id).toBe(111);
    expect(capturedBody!.first_name).toBe('Bob');
    expect(capturedBody!.state).toBe('link_state_xyz');
    expect(capturedBody!.hash).toBe('hash_abc');
  });

  it('test_telegram_link_callback_missing_fields_rejects_with_422', async () => {
    // Arrange -- missing hash and state
    server.use(
      http.post(`${API_BASE}/oauth/telegram/callback`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        if (!body.hash || !body.state) {
          return HttpResponse.json(
            { detail: 'Missing required fields' },
            { status: 422 },
          );
        }
        return HttpResponse.json({ status: 'linked', provider: 'telegram' });
      }),
    );

    // The authApi still sends what we give it. For edge case testing,
    // we test that the handler properly rejects when fields are missing.
    const data = {
      id: 111,
      first_name: 'Bob',
      auth_date: 1700000000,
      hash: '',
      state: '',
    };

    // Act & Assert
    try {
      await authApi.telegramLinkCallback(data);
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_telegram_link_callback_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/oauth/telegram/callback`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    const data = {
      id: 111,
      first_name: 'Bob',
      auth_date: 1700000000,
      hash: 'hash',
      state: 'state',
    };

    // Act & Assert
    try {
      await authApi.telegramLinkCallback(data);
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});

// ===========================================================================
// authApi.unlinkProvider
// ===========================================================================

describe('authApi.unlinkProvider', () => {
  it('test_unlink_provider_success_returns_unlinked_status', async () => {
    // Arrange & Act
    const response = await authApi.unlinkProvider('telegram');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('unlinked');
    expect(response.data.provider).toBe('telegram');
  });

  it('test_unlink_provider_google_returns_unlinked_status', async () => {
    // Act
    const response = await authApi.unlinkProvider('google');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('unlinked');
    expect(response.data.provider).toBe('google');
  });

  it('test_unlink_provider_github_returns_unlinked_status', async () => {
    // Act
    const response = await authApi.unlinkProvider('github');

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('unlinked');
    expect(response.data.provider).toBe('github');
  });

  it('test_unlink_provider_unsupported_rejects_with_400', async () => {
    // Arrange -- cast invalid provider to satisfy TS
    try {
      await authApi.unlinkProvider('unsupported_provider' as 'google');
      expect.fail('Expected 400 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
        expect(error.response?.data.detail).toBe('Unsupported OAuth provider');
      }
    }
  });

  it('test_unlink_provider_unauthenticated_rejects', async () => {
    // Arrange -- override to return 401. The 401 interceptor will try
    // to refresh but find no refresh token.
    server.use(
      http.delete(`${API_BASE}/oauth/:provider`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(authApi.unlinkProvider('telegram')).rejects.toThrow('No refresh token');
  });

  it('test_unlink_provider_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.delete(`${API_BASE}/oauth/:provider`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '45' } },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.unlinkProvider('telegram');
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(45);
    }
  });

  it('test_unlink_provider_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.delete(`${API_BASE}/oauth/:provider`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await authApi.unlinkProvider('google');
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
