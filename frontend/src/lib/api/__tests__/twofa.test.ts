/**
 * Two-Factor Authentication API Client Unit Tests
 *
 * Tests the twofaApi methods from src/lib/api/twofa.ts
 * Covers TOTP 2FA setup, verification, validation, disable, and status
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { twofaApi } from '../twofa';
import { AxiosError } from 'axios';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = 'http://localhost:8000/api/v1';

/** Type guard for AxiosError */
function isAxiosError(error: unknown): error is AxiosError<{ detail: string }> {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as Record<string, unknown>).isAxiosError === true
  );
}

/** Mock 2FA setup response */
const MOCK_2FA_SETUP = {
  secret: 'JBSWY3DPEHPK3PXP',
  qr_uri: 'otpauth://totp/VPN:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=VPN',
  message: '2FA setup initiated',
};

/** Mock 2FA status */
const MOCK_2FA_STATUS = {
  status: 'enabled' as const,
  recovery_codes: ['12345678', '87654321'],
};

// ---------------------------------------------------------------------------
// Global setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

// ===========================================================================
// twofaApi.reauth
// ===========================================================================

describe('twofaApi.reauth', () => {
  it('test_reauth_success_returns_confirmation', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/reauth`, async () => {
        return HttpResponse.json({
          message: 'Re-authenticated successfully',
          valid_for_minutes: 15,
        });
      }),
    );

    // Act
    const response = await twofaApi.reauth({ password: 'correct_password' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toContain('Re-authenticated');
    expect(response.data.valid_for_minutes).toBe(15);
  });

  it('test_reauth_sends_correct_password', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/2fa/reauth`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          message: 'Re-authenticated',
          valid_for_minutes: 15,
        });
      }),
    );

    // Act
    await twofaApi.reauth({ password: 'test_password' });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.password).toBe('test_password');
  });

  it('test_reauth_incorrect_password_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/reauth`, async () => {
        return HttpResponse.json(
          { detail: 'Incorrect password' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.reauth({ password: 'wrong_password' });
      expect.fail('Expected 401');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });

  it('test_reauth_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/reauth`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '60' } },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.reauth({ password: 'test_password' });
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(60);
    }
  });
});

// ===========================================================================
// twofaApi.setup
// ===========================================================================

describe('twofaApi.setup', () => {
  it('test_setup_2fa_success_returns_secret_and_qr', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/setup`, async () => {
        return HttpResponse.json(MOCK_2FA_SETUP);
      }),
    );

    // Act
    const response = await twofaApi.setup();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.secret).toBe('JBSWY3DPEHPK3PXP');
    expect(response.data.qr_uri).toContain('otpauth://');
    expect(response.data.message).toBe('2FA setup initiated');
  });

  it('test_setup_2fa_already_enabled_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/setup`, async () => {
        return HttpResponse.json(
          { detail: '2FA already enabled' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.setup();
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('already enabled');
      }
    }
  });

  it('test_setup_2fa_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/setup`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(twofaApi.setup()).rejects.toThrow('No refresh token');
  });
});

// ===========================================================================
// twofaApi.verify
// ===========================================================================

describe('twofaApi.verify', () => {
  it('test_verify_2fa_success_enables_2fa', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/verify`, async () => {
        return HttpResponse.json({
          status: 'enabled',
          recovery_codes: ['12345678', '87654321'],
        });
      }),
    );

    // Act
    const response = await twofaApi.verify({ code: '123456' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('enabled');
    expect(response.data.recovery_codes).toHaveLength(2);
  });

  it('test_verify_2fa_sends_correct_code', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/2fa/verify`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          status: 'enabled',
        });
      }),
    );

    // Act
    await twofaApi.verify({ code: '654321' });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.code).toBe('654321');
  });

  it('test_verify_2fa_invalid_code_rejects_with_400', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/verify`, async () => {
        return HttpResponse.json(
          { detail: 'Invalid verification code' },
          { status: 400 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.verify({ code: 'invalid' });
      expect.fail('Expected 400');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(400);
      }
    }
  });

  it('test_verify_2fa_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/verify`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '30' } },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.verify({ code: '123456' });
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(30);
    }
  });
});

// ===========================================================================
// twofaApi.validate
// ===========================================================================

describe('twofaApi.validate', () => {
  it('test_validate_2fa_code_success_returns_valid', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/validate`, async () => {
        return HttpResponse.json({ valid: true });
      }),
    );

    // Act
    const response = await twofaApi.validate({ code: '123456' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.valid).toBe(true);
  });

  it('test_validate_2fa_code_invalid_returns_false', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/validate`, async () => {
        return HttpResponse.json({ valid: false });
      }),
    );

    // Act
    const response = await twofaApi.validate({ code: 'wrong_code' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.valid).toBe(false);
  });

  it('test_validate_2fa_sends_correct_code', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/2fa/validate`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ valid: true });
      }),
    );

    // Act
    await twofaApi.validate({ code: '999888' });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.code).toBe('999888');
  });

  it('test_validate_2fa_not_enabled_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/validate`, async () => {
        return HttpResponse.json(
          { detail: '2FA not enabled' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.validate({ code: '123456' });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_validate_2fa_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/validate`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '15' } },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.validate({ code: '123456' });
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(15);
    }
  });
});

// ===========================================================================
// twofaApi.disable
// ===========================================================================

describe('twofaApi.disable', () => {
  it('test_disable_2fa_success_disables_2fa', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/disable`, async () => {
        return HttpResponse.json({
          status: 'disabled',
        });
      }),
    );

    // Act
    const response = await twofaApi.disable({ password: 'my_password', code: '123456' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('disabled');
  });

  it('test_disable_2fa_sends_correct_password', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post(`${API_BASE}/2fa/disable`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          status: 'disabled',
        });
      }),
    );

    // Act
    await twofaApi.disable({ password: 'secure_password', code: '123456' });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.password).toBe('secure_password');
    expect(capturedBody!.code).toBe('123456');
  });

  it('test_disable_2fa_incorrect_password_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/disable`, async () => {
        return HttpResponse.json(
          { detail: 'Incorrect password' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.disable({ password: 'wrong_password', code: '123456' });
      expect.fail('Expected 401');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });

  it('test_disable_2fa_not_enabled_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/disable`, async () => {
        return HttpResponse.json(
          { detail: '2FA not enabled' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.disable({ password: 'my_password', code: '123456' });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_disable_2fa_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/2fa/disable`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(
      twofaApi.disable({ password: 'my_password', code: '123456' }),
    ).rejects.toThrow('No refresh token');
  });
});

// ===========================================================================
// twofaApi.getStatus
// ===========================================================================

describe('twofaApi.getStatus', () => {
  it('test_get_2fa_status_enabled_returns_status', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/2fa/status`, () => {
        return HttpResponse.json(MOCK_2FA_STATUS);
      }),
    );

    // Act
    const response = await twofaApi.getStatus();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('enabled');
    expect(response.data.recovery_codes).toHaveLength(2);
  });

  it('test_get_2fa_status_disabled_returns_disabled_status', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/2fa/status`, () => {
        return HttpResponse.json({
          status: 'disabled',
        });
      }),
    );

    // Act
    const response = await twofaApi.getStatus();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.status).toBe('disabled');
  });

  it('test_get_2fa_status_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/2fa/status`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(twofaApi.getStatus()).rejects.toThrow('No refresh token');
  });

  it('test_get_2fa_status_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/2fa/status`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await twofaApi.getStatus();
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
