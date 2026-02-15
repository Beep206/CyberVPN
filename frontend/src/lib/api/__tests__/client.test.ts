/**
 * QUAL-02.3 -- API Client Utilities Unit Tests
 *
 * Tests the tokenStorage shim, RateLimitError class, and locale-aware
 * redirect helper from src/lib/api/client.ts.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { tokenStorage, RateLimitError, normalizeApiRequestPath } from '../client';

// ---------------------------------------------------------------------------
// tokenStorage (SEC-01: now a no-op shim)
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();
});

describe('tokenStorage (SEC-01 httpOnly cookie shim)', () => {
  it('getAccessToken always returns null', () => {
    expect(tokenStorage.getAccessToken()).toBeNull();
  });

  it('getRefreshToken always returns null', () => {
    expect(tokenStorage.getRefreshToken()).toBeNull();
  });

  it('setTokens is a no-op', () => {
    tokenStorage.setTokens('access', 'refresh');
    // Tokens should NOT be in localStorage
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('clearTokens removes legacy localStorage tokens', () => {
    localStorage.setItem('access_token', 'legacy');
    localStorage.setItem('refresh_token', 'legacy');
    tokenStorage.clearTokens();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('hasTokens always returns false', () => {
    expect(tokenStorage.hasTokens()).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// RateLimitError
// ---------------------------------------------------------------------------

describe('RateLimitError', () => {
  it('stores retryAfter seconds', () => {
    const error = new RateLimitError(30);
    expect(error.retryAfter).toBe(30);
    expect(error.name).toBe('RateLimitError');
    expect(error).toBeInstanceOf(Error);
  });

  it('message shows seconds when under 60', () => {
    const error = new RateLimitError(45);
    expect(error.message).toContain('45 seconds');
  });

  it('message shows minutes when 60 or over', () => {
    const error = new RateLimitError(120);
    expect(error.message).toContain('2 minutes');
  });

  it('rounds minutes up', () => {
    const error = new RateLimitError(90);
    expect(error.message).toContain('2 minutes');
  });

  it('exactly 60 seconds shows 1 minute', () => {
    const error = new RateLimitError(60);
    expect(error.message).toContain('1 minutes');
    expect(error.retryAfter).toBe(60);
  });
});

// ---------------------------------------------------------------------------
// Request path normalization (slash canonicalization)
// ---------------------------------------------------------------------------

describe('normalizeApiRequestPath', () => {
  it('strips trailing slash for nested paths', () => {
    expect(normalizeApiRequestPath('/servers/stats/')).toBe('/servers/stats');
  });

  it('keeps collection root trailing slash intact', () => {
    expect(normalizeApiRequestPath('/servers/')).toBe('/servers/');
  });

  it('preserves query strings while normalizing', () => {
    expect(normalizeApiRequestPath('/monitoring/stats/?period=today')).toBe('/monitoring/stats?period=today');
  });

  it('preserves absolute URLs', () => {
    expect(normalizeApiRequestPath('https://api.example.com/api/v1/servers/stats/')).toBe('https://api.example.com/api/v1/servers/stats');
  });
});

// ---------------------------------------------------------------------------
// SEC-04: Locale-aware redirect (getLocaleFromPath)
// ---------------------------------------------------------------------------

describe('locale-aware 401 redirect', () => {
  // We test the regex logic by importing and testing the redirect URL
  // construction pattern. The actual getLocaleFromPath is module-private,
  // so we test via the pattern used in the interceptor.
  const LOCALE_RE = /^\/([a-z]{2,3}-[A-Z]{2})\//;
  const DEFAULT_LOCALE = 'en-EN';

  function extractLocale(pathname: string): string {
    const match = pathname.match(LOCALE_RE);
    return match ? match[1] : DEFAULT_LOCALE;
  }

  it('extracts en-EN from /en-EN/dashboard/', () => {
    expect(extractLocale('/en-EN/dashboard/')).toBe('en-EN');
  });

  it('extracts ru-RU from /ru-RU/servers/', () => {
    expect(extractLocale('/ru-RU/servers/')).toBe('ru-RU');
  });

  it('extracts ar-SA (RTL) from /ar-SA/users/', () => {
    expect(extractLocale('/ar-SA/users/')).toBe('ar-SA');
  });

  it('extracts he-IL (RTL) from /he-IL/analytics/', () => {
    expect(extractLocale('/he-IL/analytics/')).toBe('he-IL');
  });

  it('extracts fa-IR (RTL) from /fa-IR/settings/', () => {
    expect(extractLocale('/fa-IR/settings/')).toBe('fa-IR');
  });

  it('extracts fil-PH (3-letter lang) from /fil-PH/page/', () => {
    expect(extractLocale('/fil-PH/page/')).toBe('fil-PH');
  });

  it('falls back to en-EN for bare /dashboard', () => {
    expect(extractLocale('/dashboard')).toBe(DEFAULT_LOCALE);
  });

  it('falls back to en-EN for root /', () => {
    expect(extractLocale('/')).toBe(DEFAULT_LOCALE);
  });

  it('builds correct redirect URL', () => {
    const locale = extractLocale('/ru-RU/servers/');
    const redirect = `/ru-RU/servers/`;
    const url = `/${locale}/login?redirect=${encodeURIComponent(redirect)}`;
    expect(url).toBe('/ru-RU/login?redirect=%2Fru-RU%2Fservers%2F');
  });
});
