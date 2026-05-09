import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import enCookiePolicy from '../../../../messages/en-EN/CookiePolicy.json';
import enFooter from '../../../../messages/en-EN/footer.json';
import ruCookiePolicy from '../../../../messages/ru-RU/CookiePolicy.json';
import ruFooter from '../../../../messages/ru-RU/footer.json';

type Messages = Record<string, unknown>;

const requiredPhrases = [
  'controlled public beta',
  'cookie policy',
  'cyber-vpn.net',
  'cyber-vpn.org',
  'admin.cyber-vpn.net',
  'admin.cyber-vpn.org',
  'next-intl',
  'next_locale',
  'access_token',
  'refresh_token',
  'httponly',
  'samesite=lax',
  'secure in production',
  'path /api',
  '15 minutes',
  '7 days',
  'oauth_tx',
  'pending_2fa',
  'oauth_result',
  'csrf',
  'origin/referer',
  'sentry',
  'web vitals',
  'senddefaultpii=false',
  'pii scrubbing',
  'telegram mini app',
  'posthog',
  'ga4',
  'disabled unless',
  'strictly necessary',
  'non-essential',
  'consent',
  'cookie inventory',
  'set-cookie',
  'privacy policy',
  'terms of service',
  'acceptable use policy',
  'refund policy',
];

const unsafePhrases = [
  'we do not use cookies',
  'no cookies',
  'no tracking of any kind',
  'all cookies are strictly necessary',
  'analytics cookies are always enabled',
  'marketing cookies are always enabled',
  'without consent',
  'we sell tracking data',
  'cookie policy is final',
  'TOP SECRET',
  '[Your Company Address]',
  'cybervpn.app',
];

function flattenMessages(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(flattenMessages).join('\n');
  }

  if (typeof value === 'object' && value !== null) {
    return Object.values(value).map(flattenMessages).join('\n');
  }

  return '';
}

function readLocaleFile(fileName: string): Array<{ locale: string; messages: Messages }> {
  const messagesRoot = join(process.cwd(), 'messages');

  return readdirSync(messagesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .filter((entry) => existsSync(join(messagesRoot, entry.name, fileName)))
    .map((entry) => {
      const filePath = join(messagesRoot, entry.name, fileName);
      const messages = JSON.parse(readFileSync(filePath, 'utf8')) as Messages;

      return { locale: entry.name, messages };
    });
}

describe('stage1 cookie policy copy', () => {
  it('states required S1 cookie/storage inventory, consent rules and evidence blockers', () => {
    const combined = `${flattenMessages(enCookiePolicy)}\n${flattenMessages(ruCookiePolicy)}`.toLowerCase();

    for (const phrase of requiredPhrases) {
      expect(combined).toContain(phrase);
    }
  });

  it('adds footer navigation to the cookie policy page', () => {
    expect(enFooter.links.cookiePolicy).toBe('Cookie Policy');
    expect(ruFooter.links.cookiePolicy).toBe('Политика cookies');
  });

  it('keeps non-essential tracking disabled unless consent and evidence exist', () => {
    const combined = `${flattenMessages(enCookiePolicy)}\n${flattenMessages(ruCookiePolicy)}`.toLowerCase();

    expect(combined).toContain('non-essential analytics, marketing, profiling or advertising cookies must not be enabled by default');
    expect(combined).toContain('posthog, ga4, marketing pixels and advertising tracking are disabled unless');
    expect(combined).toContain('consent banner/settings evidence proving default-off behavior and withdrawal controls');
  });

  it('removes unsafe cookie/privacy promises from all locale copies', () => {
    const localeFiles = [
      ...readLocaleFile('CookiePolicy.json'),
      ...readLocaleFile('footer.json'),
    ];

    for (const { locale, messages } of localeFiles) {
      const text = flattenMessages(messages).toLowerCase();

      for (const phrase of unsafePhrases) {
        expect(text, `${locale} contains unsafe phrase: ${phrase}`).not.toContain(phrase.toLowerCase());
      }
    }
  });
});
