/**
 * Security API Client Unit Tests
 *
 * Tests the securityApi methods from src/lib/api/security.ts
 * Covers password changes and antiphishing code management
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { securityApi } from '../security';
import { RateLimitError } from '../client';
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
// securityApi.changePassword
// ===========================================================================

describe('securityApi.changePassword', () => {
  it('test_change_password_success_returns_200', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/change-password`, () => {
        return HttpResponse.json({ message: 'Password changed successfully.' });
      }),
    );

    // Act
    const response = await securityApi.changePassword({
      current_password: 'OldPassword123!',
      new_password: 'NewPassword456!',
      new_password_confirm: 'NewPassword456!',
    });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Password changed successfully.');
  });

  it('test_change_password_invalid_current_password_returns_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/change-password`, () => {
        return HttpResponse.json(
          { detail: 'Invalid current password.' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.changePassword({
        current_password: 'WrongPassword',
        new_password: 'NewPassword456!',
        new_password_confirm: 'NewPassword456!',
      });
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
        expect(error.response?.data.detail).toBe('Invalid current password.');
      }
    }
  });

  it('test_change_password_rate_limit_exceeded_returns_429', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/change-password`, () => {
        return HttpResponse.json(
          { detail: 'Rate limit exceeded. Try again in 3600 seconds.' },
          {
            status: 429,
            headers: { 'Retry-After': '3600' },
          },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.changePassword({
        current_password: 'OldPassword123!',
        new_password: 'NewPassword456!',
        new_password_confirm: 'NewPassword456!',
      });
      expect.fail('Should have thrown an error');
    } catch (error) {
      // Client transforms 429 into RateLimitError
      expect(error).toBeInstanceOf(RateLimitError);
      if (error instanceof RateLimitError) {
        expect(error.retryAfter).toBe(3600);
        expect(error.message).toContain('60 minutes');
      }
    }
  });

  it('test_change_password_validation_error_returns_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/auth/change-password`, () => {
        return HttpResponse.json(
          { detail: 'Password must be at least 8 characters.' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.changePassword({
        current_password: 'OldPassword123!',
        new_password: 'short',
        new_password_confirm: 'short',
      });
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('at least 8 characters');
      }
    }
  });
});

// ===========================================================================
// securityApi.getAntiphishingCode
// ===========================================================================

describe('securityApi.getAntiphishingCode', () => {
  it('test_get_antiphishing_code_success_returns_code', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ code: 'SAFE123' });
      }),
    );

    // Act
    const response = await securityApi.getAntiphishingCode();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.code).toBe('SAFE123');
  });

  it('test_get_antiphishing_code_not_set_returns_null', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ code: null });
      }),
    );

    // Act
    const response = await securityApi.getAntiphishingCode();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.code).toBeNull();
  });

  it('test_get_antiphishing_code_unauthorized_returns_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.getAntiphishingCode();
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });
});

// ===========================================================================
// securityApi.setAntiphishingCode
// ===========================================================================

describe('securityApi.setAntiphishingCode', () => {
  it('test_set_antiphishing_code_success_returns_200', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ message: 'Antiphishing code updated.' });
      }),
    );

    // Act
    const response = await securityApi.setAntiphishingCode({ code: 'MYSAFE456' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Antiphishing code updated.');
  });

  it('test_set_antiphishing_code_creates_new_code', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ message: 'Antiphishing code created.' });
      }),
    );

    // Act
    const response = await securityApi.setAntiphishingCode({ code: 'NEWCODE789' });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Antiphishing code created.');
  });

  it('test_set_antiphishing_code_invalid_format_returns_422', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json(
          { detail: 'Code must be between 4 and 32 characters.' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.setAntiphishingCode({ code: '123' });
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
        expect(error.response?.data.detail).toContain('between 4 and 32');
      }
    }
  });

  it('test_set_antiphishing_code_unauthorized_returns_401', async () => {
    // Arrange
    server.use(
      http.post(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.setAntiphishingCode({ code: 'SAFE123' });
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });
});

// ===========================================================================
// securityApi.deleteAntiphishingCode
// ===========================================================================

describe('securityApi.deleteAntiphishingCode', () => {
  it('test_delete_antiphishing_code_success_returns_200', async () => {
    // Arrange
    server.use(
      http.delete(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json({ message: 'Antiphishing code removed.' });
      }),
    );

    // Act
    const response = await securityApi.deleteAntiphishingCode();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.message).toBe('Antiphishing code removed.');
  });

  it('test_delete_antiphishing_code_not_set_returns_404', async () => {
    // Arrange
    server.use(
      http.delete(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json(
          { detail: 'Code not set' },
          { status: 404 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.deleteAntiphishingCode();
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(404);
      }
    }
  });

  it('test_delete_antiphishing_code_unauthorized_returns_401', async () => {
    // Arrange
    server.use(
      http.delete(`${API_BASE}/security/antiphishing`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    try {
      await securityApi.deleteAntiphishingCode();
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(401);
      }
    }
  });
});
