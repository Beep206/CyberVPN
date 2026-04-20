import { describe, expect, it } from 'vitest';
import robots from '../robots';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

function asArray(value: string | string[] | undefined): string[] {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

describe('robots', () => {
  it('points to the canonical sitemap and blocks private/test routes across locales', () => {
    const policy = robots();
    const [rule] = policy.rules;
    const disallow = asArray(rule.disallow);

    expect(policy.sitemap).toBe(`${SITE_URL}/sitemap.xml`);
    expect(rule.userAgent).toBe('*');
    expect(rule.allow).toBe('/');

    expect(disallow).toEqual(
      expect.arrayContaining([
        '/analytics',
        '/dashboard',
        '/settings',
        '/miniapp',
        '/login',
        '/register',
        '/reset-password',
        '/forgot-password',
        '/oauth',
        '/magic-link',
        '/telegram-link',
        '/telegram-widget',
        '/test-animation',
        '/test-error',
        '/en-EN/analytics',
        '/en-EN/dashboard',
        '/en-EN/settings',
        '/en-EN/wallet',
        '/en-EN/miniapp',
        '/en-EN/login',
        '/en-EN/test-error',
        '/ru-RU/analytics',
        '/ru-RU/dashboard',
        '/ru-RU/miniapp',
        '/ru-RU/users',
      ]),
    );

    expect(disallow).not.toEqual(
      expect.arrayContaining(['/pricing', '/en-EN/pricing', '/help', '/en-EN/help']),
    );
  });
});
