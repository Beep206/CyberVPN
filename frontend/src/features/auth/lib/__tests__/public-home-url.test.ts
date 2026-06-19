import { describe, expect, it } from 'vitest';
import { getPublicHomeHref } from '../public-home-url';

describe('getPublicHomeHref', () => {
  it('builds public canonical home links for supported locales', () => {
    expect(getPublicHomeHref('ru-RU')).toBe('https://cyber-vpn.net/ru-RU');
  });

  it('falls back to the default locale for unsupported locale params', () => {
    expect(getPublicHomeHref('zh-ZZ')).toBe('https://cyber-vpn.net/en-EN');
  });
});
