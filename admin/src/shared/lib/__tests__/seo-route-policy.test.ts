import { describe, expect, it } from 'vitest';
import {
  buildLocalizedAlternates,
  getLocalizedPathInfo,
  isIndexableLocalizedPath,
  isRolloutIndexableLocalizedPath,
  SITE_URL,
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

    expect(alternates['en-EN']).toBe(`${SITE_URL}/en-EN/pricing`);
    expect(alternates['ru-RU']).toBe(`${SITE_URL}/ru-RU/pricing`);
    expect(alternates['x-default']).toBe(`${SITE_URL}/ru-RU/pricing`);
    expect(guidesAlternates['en-EN']).toBe(`${SITE_URL}/en-EN/guides`);
    expect(guidesAlternates['ru-RU']).toBe(`${SITE_URL}/ru-RU/guides`);
    expect(guidesAlternates['zh-CN']).toBeUndefined();
    expect(guidesAlternates['x-default']).toBe(`${SITE_URL}/ru-RU/guides`);
    expect(guideDetailAlternates['en-EN']).toBe(
      `${SITE_URL}/en-EN/guides/how-to-bypass-dpi-with-vless-reality`,
    );
    expect(guideDetailAlternates['ru-RU']).toBe(
      `${SITE_URL}/ru-RU/guides/how-to-bypass-dpi-with-vless-reality`,
    );
    expect(guideDetailAlternates['zh-CN']).toBeUndefined();
    expect(guideDetailAlternates['hi-IN']).toBeUndefined();
    expect(guideDetailAlternates['ja-JP']).toBeUndefined();
    expect(guideDetailAlternates['fa-IR']).toBeUndefined();
    expect(toAbsoluteLocalizedUrl('en-EN', '/pricing')).toBe(`${SITE_URL}/en-EN/pricing`);
  });

  it('differentiates structurally public routes from rollout-eligible locales', () => {
    expect(isRolloutIndexableLocalizedPath('/ru-RU/pricing')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/analytics')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/wallet')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/guides')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/ja-JP/guides')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ru-RU/guides/how-to-bypass-dpi-with-vless-reality')).toBe(true);
    expect(isRolloutIndexableLocalizedPath('/zh-CN/compare/vless-reality-vs-wireguard')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/hi-IN/guides/how-to-bypass-dpi-with-vless-reality')).toBe(false);
    expect(isRolloutIndexableLocalizedPath('/ja-JP/devices/android-vpn-setup')).toBe(false);
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
