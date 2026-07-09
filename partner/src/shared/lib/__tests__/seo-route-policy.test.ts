import { describe, expect, it } from 'vitest';
import {
  buildLocalizedAlternates,
  getLocalizedPathInfo,
  isIndexableLocalizedPath,
  isRolloutIndexableLocalizedPath,
  toAbsoluteLocalizedUrl,
  toLocalizedPath,
} from '@/shared/lib/seo-route-policy';

describe('seo-route-policy', () => {
  it('treats storefront public routes as indexable and private or copied marketing routes as non-indexable', () => {
    expect(isIndexableLocalizedPath('/en-EN')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/checkout')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/legal-docs')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/support')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/pricing')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/help')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/guides')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      false,
    );

    expect(isIndexableLocalizedPath('/en-EN/analytics')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/wallet')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/users')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/dashboard')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/dashboard/servers')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/miniapp/home')).toBe(false);
    expect(isIndexableLocalizedPath('/en-EN/test-error')).toBe(false);
  });

  it('normalizes localized paths consistently', () => {
    expect(toLocalizedPath('en-EN', '/checkout')).toBe('/en-EN/checkout');
    expect(toLocalizedPath('ru-RU', 'support')).toBe('/ru-RU/support');
    expect(toLocalizedPath('en-EN', '/en-EN/legal-docs')).toBe('/en-EN/legal-docs');
  });

  it('builds absolute alternate URLs for every configured locale plus x-default', () => {
    const alternates = buildLocalizedAlternates('/checkout');
    const supportAlternates = buildLocalizedAlternates('/support');
    const legalAlternates = buildLocalizedAlternates('/legal-docs');

    expect(alternates['en-EN']).toBe('https://partner.cyber-vpn.net/en-EN/checkout');
    expect(alternates['ru-RU']).toBe('https://partner.cyber-vpn.net/ru-RU/checkout');
    expect(alternates['x-default']).toBe('https://partner.cyber-vpn.net/ru-RU/checkout');
    expect(supportAlternates['en-EN']).toBe('https://partner.cyber-vpn.net/en-EN/support');
    expect(supportAlternates['ru-RU']).toBe('https://partner.cyber-vpn.net/ru-RU/support');
    expect(supportAlternates['zh-CN']).toBeUndefined();
    expect(supportAlternates['x-default']).toBe('https://partner.cyber-vpn.net/ru-RU/support');
    expect(legalAlternates['en-EN']).toBe('https://partner.cyber-vpn.net/en-EN/legal-docs');
    expect(legalAlternates['ru-RU']).toBe('https://partner.cyber-vpn.net/ru-RU/legal-docs');
    expect(legalAlternates['zh-CN']).toBeUndefined();
    expect(toAbsoluteLocalizedUrl('en-EN', '/checkout')).toBe(
      'https://partner.cyber-vpn.net/en-EN/checkout',
    );
  });

  it('differentiates structurally public routes from rollout-eligible locales', () => {
    expect(isRolloutIndexableLocalizedPath('/ru-RU')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/checkout')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/legal-docs')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/support')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/pricing')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/analytics')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/wallet')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/guides')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ja-JP/guides')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/guides/how-to-bypass-dpi-with-vless-reality')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/zh-CN/compare/vless-reality-vs-wireguard')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/hi-IN/guides/how-to-bypass-dpi-with-vless-reality')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ja-JP/devices/android-vpn-setup')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/fa-IR/guides/how-to-bypass-dpi-with-vless-reality')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/en-EN/guides')).toBe(false);
  });

  it('provides normalized path info for later metadata helpers', () => {
    expect(getLocalizedPathInfo('/en-EN/checkout')).toEqual({
      locale: 'en-EN',
      pathname: '/checkout',
      isLocalized: true,
    });

    expect(getLocalizedPathInfo('/checkout')).toEqual({
      locale: undefined,
      pathname: '/checkout',
      isLocalized: false,
    });
  });
});
