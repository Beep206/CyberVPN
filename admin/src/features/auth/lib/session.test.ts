import { describe, expect, it } from 'vitest';

import { getSafeRedirectPath } from './redirect-path';
import { buildInternalLoginHref, buildLocalizedLoginRedirect } from './session';

describe('auth redirect canonicalization', () => {
  it('builds a locale-prefixed browser redirect from a raw pathname without locale', () => {
    expect(buildLocalizedLoginRedirect('/dashboard')).toBe(
      '/en-EN/login?redirect=%2Fen-EN%2Fdashboard',
    );
  });

  it('builds an internal next-intl href without duplicating the locale prefix', () => {
    expect(buildInternalLoginHref('/dashboard', 'ru-RU')).toBe(
      '/login?redirect=%2Fru-RU%2Fdashboard',
    );
  });

  it('normalizes redirect targets to the active locale', () => {
    expect(getSafeRedirectPath('/dashboard/servers?tab=active', 'ru-RU')).toBe(
      '/ru-RU/dashboard/servers?tab=active',
    );
  });

  it('rewrites foreign locale prefixes to the active locale', () => {
    expect(getSafeRedirectPath('/en-EN/dashboard', 'ru-RU')).toBe(
      '/ru-RU/dashboard',
    );
  });

  it('falls back to the locale dashboard when redirect points to an auth route', () => {
    expect(getSafeRedirectPath('/ru-RU/login', 'ru-RU')).toBe('/ru-RU/dashboard');
  });
});
