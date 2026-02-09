/**
 * QUAL-02.3 -- API Client Utilities Unit Tests
 *
 * Tests the tokenStorage helper and RateLimitError class from
 * src/lib/api/client.ts. These are pure-logic units that underpin
 * the auth API client -- the interceptor tests live in auth.test.ts.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { tokenStorage, RateLimitError } from '../client';

// ---------------------------------------------------------------------------
// tokenStorage
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();
});

describe('tokenStorage', () => {
  describe('getAccessToken', () => {
    it('test_get_access_token_returns_null_when_empty', () => {
      // Act
      const token = tokenStorage.getAccessToken();

      // Assert
      expect(token).toBeNull();
    });

    it('test_get_access_token_returns_stored_value', () => {
      // Arrange
      localStorage.setItem('access_token', 'abc123');

      // Act
      const token = tokenStorage.getAccessToken();

      // Assert
      expect(token).toBe('abc123');
    });
  });

  describe('getRefreshToken', () => {
    it('test_get_refresh_token_returns_null_when_empty', () => {
      // Act
      const token = tokenStorage.getRefreshToken();

      // Assert
      expect(token).toBeNull();
    });

    it('test_get_refresh_token_returns_stored_value', () => {
      // Arrange
      localStorage.setItem('refresh_token', 'refresh_xyz');

      // Act
      const token = tokenStorage.getRefreshToken();

      // Assert
      expect(token).toBe('refresh_xyz');
    });
  });

  describe('setTokens', () => {
    it('test_set_tokens_stores_both_tokens', () => {
      // Act
      tokenStorage.setTokens('access_tok', 'refresh_tok');

      // Assert
      expect(localStorage.getItem('access_token')).toBe('access_tok');
      expect(localStorage.getItem('refresh_token')).toBe('refresh_tok');
    });

    it('test_set_tokens_overwrites_existing_tokens', () => {
      // Arrange
      tokenStorage.setTokens('old_access', 'old_refresh');

      // Act
      tokenStorage.setTokens('new_access', 'new_refresh');

      // Assert
      expect(localStorage.getItem('access_token')).toBe('new_access');
      expect(localStorage.getItem('refresh_token')).toBe('new_refresh');
    });
  });

  describe('clearTokens', () => {
    it('test_clear_tokens_removes_both_tokens', () => {
      // Arrange
      tokenStorage.setTokens('access', 'refresh');

      // Act
      tokenStorage.clearTokens();

      // Assert
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });

    it('test_clear_tokens_is_safe_when_no_tokens_stored', () => {
      // Act -- should not throw when nothing to remove
      expect(() => tokenStorage.clearTokens()).not.toThrow();
    });
  });

  describe('hasTokens', () => {
    it('test_has_tokens_returns_false_when_empty', () => {
      // Act & Assert
      expect(tokenStorage.hasTokens()).toBe(false);
    });

    it('test_has_tokens_returns_true_when_access_token_exists', () => {
      // Arrange
      tokenStorage.setTokens('some_access', 'some_refresh');

      // Act & Assert
      expect(tokenStorage.hasTokens()).toBe(true);
    });

    it('test_has_tokens_returns_false_after_clear', () => {
      // Arrange
      tokenStorage.setTokens('a', 'b');
      tokenStorage.clearTokens();

      // Act & Assert
      expect(tokenStorage.hasTokens()).toBe(false);
    });
  });
});

// ---------------------------------------------------------------------------
// RateLimitError
// ---------------------------------------------------------------------------

describe('RateLimitError', () => {
  it('test_rate_limit_error_stores_retry_after_seconds', () => {
    // Act
    const error = new RateLimitError(30);

    // Assert
    expect(error.retryAfter).toBe(30);
    expect(error.name).toBe('RateLimitError');
    expect(error).toBeInstanceOf(Error);
  });

  it('test_rate_limit_error_message_shows_seconds_when_under_60', () => {
    // Act
    const error = new RateLimitError(45);

    // Assert
    expect(error.message).toContain('45 seconds');
  });

  it('test_rate_limit_error_message_shows_minutes_when_60_or_over', () => {
    // Act
    const error = new RateLimitError(120);

    // Assert
    expect(error.message).toContain('2 minutes');
  });

  it('test_rate_limit_error_message_rounds_minutes_up', () => {
    // Act -- 90 seconds = 1.5 minutes, should round up to 2
    const error = new RateLimitError(90);

    // Assert
    expect(error.message).toContain('2 minutes');
  });

  it('test_rate_limit_error_exactly_60_seconds_shows_1_minute', () => {
    // Act
    const error = new RateLimitError(60);

    // Assert
    expect(error.message).toContain('1 minutes');
    expect(error.retryAfter).toBe(60);
  });
});
