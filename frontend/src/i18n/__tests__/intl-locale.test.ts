import { describe, expect, it } from 'vitest';

import { toIntlLocale } from '../intl-locale';

describe('toIntlLocale', () => {
  it('maps the app routing locale en-EN to a valid Intl locale', () => {
    expect(toIntlLocale('en-EN')).toBe('en-US');
    expect(() => new Intl.DateTimeFormat(toIntlLocale('en-EN'))).not.toThrow();
  });

  it('keeps valid BCP 47 locales unchanged after canonicalization', () => {
    expect(toIntlLocale('ru-RU')).toBe('ru-RU');
  });

  it('falls back for invalid locale values', () => {
    expect(toIntlLocale('not a locale')).toBe('en-US');
  });
});
