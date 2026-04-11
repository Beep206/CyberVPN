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
  it('treats public marketing routes as indexable and private routes as non-indexable', () => {
    expect(isIndexableLocalizedPath('/en-EN')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/pricing')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/help')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/guides')).toBe(true);
    expect(isIndexableLocalizedPath('/en-EN/guides/how-to-bypass-dpi-with-vless-reality')).toBe(
      true,
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
    expect(toLocalizedPath('en-EN', '/pricing')).toBe('/en-EN/pricing');
    expect(toLocalizedPath('ru-RU', 'pricing')).toBe('/ru-RU/pricing');
    expect(toLocalizedPath('en-EN', '/en-EN/help')).toBe('/en-EN/help');
  });

  it('builds absolute alternate URLs for every configured locale plus x-default', () => {
    const alternates = buildLocalizedAlternates('/pricing');
    const guidesAlternates = buildLocalizedAlternates('/guides');
    const guideDetailAlternates = buildLocalizedAlternates(
      '/guides/how-to-bypass-dpi-with-vless-reality',
    );

    expect(alternates['en-EN']).toBe('https://vpn.ozoxy.ru/en-EN/pricing');
    expect(alternates['ru-RU']).toBe('https://vpn.ozoxy.ru/ru-RU/pricing');
    expect(alternates['x-default']).toBe('https://vpn.ozoxy.ru/en-EN/pricing');
    expect(guidesAlternates['en-EN']).toBe('https://vpn.ozoxy.ru/en-EN/guides');
    expect(guidesAlternates['ru-RU']).toBe('https://vpn.ozoxy.ru/ru-RU/guides');
    expect(guidesAlternates['zh-CN']).toBe('https://vpn.ozoxy.ru/zh-CN/guides');
    expect(guidesAlternates['x-default']).toBe('https://vpn.ozoxy.ru/en-EN/guides');
    expect(guideDetailAlternates['en-EN']).toBe(
      'https://vpn.ozoxy.ru/en-EN/guides/how-to-bypass-dpi-with-vless-reality',
    );
    expect(guideDetailAlternates['ru-RU']).toBe(
      'https://vpn.ozoxy.ru/ru-RU/guides/how-to-bypass-dpi-with-vless-reality',
    );
    expect(guideDetailAlternates['zh-CN']).toBe(
      'https://vpn.ozoxy.ru/zh-CN/guides/how-to-bypass-dpi-with-vless-reality',
    );
    expect(guideDetailAlternates['hi-IN']).toBe(
      'https://vpn.ozoxy.ru/hi-IN/guides/how-to-bypass-dpi-with-vless-reality',
    );
    expect(guideDetailAlternates['ja-JP']).toBe(
      'https://vpn.ozoxy.ru/ja-JP/guides/how-to-bypass-dpi-with-vless-reality',
    );
    expect(guideDetailAlternates['fa-IR']).toBeUndefined();
    expect(toAbsoluteLocalizedUrl('hi-IN', '/pricing')).toBe(
      'https://vpn.ozoxy.ru/hi-IN/pricing',
    );
  });

  it('differentiates structurally public routes from rollout-eligible locales', () => {
    expect(isRolloutIndexableLocalizedPath('/ru-RU/pricing')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/analytics')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/wallet')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/guides')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ja-JP/guides')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/guides/how-to-bypass-dpi-with-vless-reality')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/zh-CN/compare/vless-reality-vs-wireguard')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/hi-IN/guides/how-to-bypass-dpi-with-vless-reality')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ja-JP/devices/android-vpn-setup')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/fa-IR/guides/how-to-bypass-dpi-with-vless-reality')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/en-EN/guides')).toBe(true);
  });

  it('provides normalized path info for later metadata helpers', () => {
    expect(getLocalizedPathInfo('/en-EN/pricing')).toEqual({
      locale: 'en-EN',
      pathname: '/pricing',
      isLocalized: true,
    });

    expect(getLocalizedPathInfo('/pricing')).toEqual({
      locale: undefined,
      pathname: '/pricing',
      isLocalized: false,
    });
  });
});
