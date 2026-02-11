/**
 * Profile API Client Unit Tests
 *
 * Tests the profileApi methods from src/lib/api/profile.ts
 * Covers user profile retrieval and updates
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { profileApi } from '../profile';
import { tokenStorage } from '../client';
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

/** Mock user profile */
const MOCK_PROFILE = {
  id: 'user_001',
  email: 'user@example.com',
  display_name: 'John Doe',
  avatar_url: 'https://example.com/avatar.jpg',
  language: 'en-EN',
  timezone: 'UTC',
  updated_at: '2025-02-10T10:00:00Z',
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
// profileApi.getProfile
// ===========================================================================

describe('profileApi.getProfile', () => {
  it('test_get_profile_success_returns_user_data', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/users/me/profile`, () => {
        return HttpResponse.json(MOCK_PROFILE);
      }),
    );

    // Act
    const response = await profileApi.getProfile();

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.id).toBe('user_001');
    expect(response.data.email).toBe('user@example.com');
    expect(response.data.display_name).toBe('John Doe');
    expect(response.data.language).toBe('en-EN');
    expect(response.data.timezone).toBe('UTC');
  });

  it('test_get_profile_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/users/me/profile`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(profileApi.getProfile()).rejects.toThrow('No refresh token');
  });

  it('test_get_profile_with_refresh_token_retries_on_401', async () => {
    // Arrange
    tokenStorage.setTokens('expired_access', 'valid_refresh');

    let callCount = 0;
    server.use(
      http.get(`${API_BASE}/users/me/profile`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 },
          );
        }
        return HttpResponse.json(MOCK_PROFILE);
      }),
    );

    // Act
    const response = await profileApi.getProfile();

    // Assert
    expect(callCount).toBe(2);
    expect(response.status).toBe(200);
    expect(response.data.email).toBe('user@example.com');
  });

  it('test_get_profile_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/users/me/profile`, () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await profileApi.getProfile();
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });

  it('test_get_profile_rate_limited_rejects_with_rate_limit_error', async () => {
    // Arrange
    server.use(
      http.get(`${API_BASE}/users/me/profile`, () => {
        return HttpResponse.json(
          { detail: 'Too many requests' },
          { status: 429, headers: { 'Retry-After': '30' } },
        );
      }),
    );

    // Act & Assert
    try {
      await profileApi.getProfile();
      expect.fail('Expected RateLimitError');
    } catch (error: unknown) {
      expect((error as Error).name).toBe('RateLimitError');
      expect((error as { retryAfter: number }).retryAfter).toBe(30);
    }
  });
});

// ===========================================================================
// profileApi.updateProfile
// ===========================================================================

describe('profileApi.updateProfile', () => {
  it('test_update_profile_success_returns_updated_data', async () => {
    // Arrange
    server.use(
      http.patch(`${API_BASE}/users/me/profile`, async () => {
        return HttpResponse.json({
          ...MOCK_PROFILE,
          display_name: 'Jane Smith',
          language: 'es-ES',
        });
      }),
    );

    // Act
    const response = await profileApi.updateProfile({
      display_name: 'Jane Smith',
      language: 'es-ES',
    });

    // Assert
    expect(response.status).toBe(200);
    expect(response.data.display_name).toBe('Jane Smith');
    expect(response.data.language).toBe('es-ES');
  });

  it('test_update_profile_sends_correct_body', async () => {
    // Arrange - capture request body
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.patch(`${API_BASE}/users/me/profile`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(MOCK_PROFILE);
      }),
    );

    // Act
    await profileApi.updateProfile({
      display_name: 'Updated Name',
      timezone: 'America/New_York',
    });

    // Assert
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.display_name).toBe('Updated Name');
    expect(capturedBody!.timezone).toBe('America/New_York');
  });

  it('test_update_profile_invalid_data_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.patch(`${API_BASE}/users/me/profile`, async () => {
        return HttpResponse.json(
          { detail: 'Validation error: invalid language code' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await profileApi.updateProfile({
        language: 'invalid_lang',
      });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_update_profile_invalid_timezone_rejects_with_422', async () => {
    // Arrange
    server.use(
      http.patch(`${API_BASE}/users/me/profile`, async () => {
        return HttpResponse.json(
          { detail: 'Invalid timezone' },
          { status: 422 },
        );
      }),
    );

    // Act & Assert
    try {
      await profileApi.updateProfile({
        timezone: 'invalid_timezone',
      });
      expect.fail('Expected 422');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(422);
      }
    }
  });

  it('test_update_profile_unauthenticated_rejects_with_401', async () => {
    // Arrange
    server.use(
      http.patch(`${API_BASE}/users/me/profile`, () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    // Act & Assert
    await expect(
      profileApi.updateProfile({ display_name: 'Test' }),
    ).rejects.toThrow('No refresh token');
  });

  it('test_update_profile_server_error_500_rejects', async () => {
    // Arrange
    server.use(
      http.patch(`${API_BASE}/users/me/profile`, async () => {
        return HttpResponse.json(
          { detail: 'Internal server error' },
          { status: 500 },
        );
      }),
    );

    // Act & Assert
    try {
      await profileApi.updateProfile({ display_name: 'Test' });
      expect.fail('Expected 500 error');
    } catch (error: unknown) {
      expect(isAxiosError(error)).toBe(true);
      if (isAxiosError(error)) {
        expect(error.response?.status).toBe(500);
      }
    }
  });
});
