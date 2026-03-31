import { describe, expect, it } from 'vitest';
import {
  SITE_URL,
  getHtmlLanguageAttributes,
  withSiteMetadata,
} from '@/shared/lib/site-metadata';

describe('site-metadata', () => {
  it('builds page-equivalent canonical and hreflang alternates for public routes', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Pricing',
        description: 'Pricing overview',
      },
      {
        locale: 'en-EN',
        canonicalPath: '/pricing',
        routeType: 'public',
      },
    );

    expect(metadata.metadataBase?.toString()).toBe(`${SITE_URL}/`);
    expect(metadata.alternates?.canonical).toBe(`${SITE_URL}/en-EN/pricing`);
    expect(metadata.alternates?.languages?.['en-EN']).toBe(`${SITE_URL}/en-EN/pricing`);
    expect(metadata.alternates?.languages?.['ru-RU']).toBe(`${SITE_URL}/ru-RU/pricing`);
    expect(metadata.alternates?.languages?.['x-default']).toBe(`${SITE_URL}/en-EN/pricing`);
    expect(metadata.openGraph?.images).toEqual([
      {
        url: `${SITE_URL}/en-EN/opengraph-image`,
        width: 1200,
        height: 630,
        alt: 'CyberVPN - Advanced VPN Service',
      },
    ]);
    expect(metadata.twitter?.images).toEqual([`${SITE_URL}/en-EN/opengraph-image`]);
  });

  it('keeps exact market hubs indexable in priority locales', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Guides',
        description: 'Operational guides',
      },
      {
        locale: 'ru-RU',
        canonicalPath: '/guides',
        routeType: 'public',
      },
    );

    expect(metadata.alternates?.canonical).toBe(`${SITE_URL}/ru-RU/guides`);
    expect(metadata.alternates?.languages).toMatchObject({
      'en-EN': `${SITE_URL}/en-EN/guides`,
      'ru-RU': `${SITE_URL}/ru-RU/guides`,
      'zh-CN': `${SITE_URL}/zh-CN/guides`,
      'x-default': `${SITE_URL}/en-EN/guides`,
    });
    expect(metadata.robots).toBeUndefined();
  });

  it('keeps localized detail content indexable for Russia', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Guide detail',
        description: 'Guide detail',
      },
      {
        locale: 'ru-RU',
        canonicalPath: '/guides/how-to-bypass-dpi-with-vless-reality',
        routeType: 'public',
      },
    );

    expect(metadata.alternates?.canonical).toBe(
      `${SITE_URL}/ru-RU/guides/how-to-bypass-dpi-with-vless-reality`,
    );
    expect(metadata.alternates?.languages).toMatchObject({
      'en-EN': `${SITE_URL}/en-EN/guides/how-to-bypass-dpi-with-vless-reality`,
      'ru-RU': `${SITE_URL}/ru-RU/guides/how-to-bypass-dpi-with-vless-reality`,
      'zh-CN': `${SITE_URL}/zh-CN/guides/how-to-bypass-dpi-with-vless-reality`,
      'x-default': `${SITE_URL}/en-EN/guides/how-to-bypass-dpi-with-vless-reality`,
    });
    expect(metadata.robots).toBeUndefined();
  });

  it('keeps expanded detail content indexable across the full priority rollout set', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Guide detail',
        description: 'Guide detail',
      },
      {
        locale: 'hi-IN',
        canonicalPath: '/guides/how-to-bypass-dpi-with-vless-reality',
        routeType: 'public',
      },
    );

    expect(metadata.alternates?.canonical).toBe(
      `${SITE_URL}/hi-IN/guides/how-to-bypass-dpi-with-vless-reality`,
    );
    expect(metadata.robots).toBeUndefined();
  });

  it('keeps expanded detail content noindex outside the priority rollout set', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Guide detail',
        description: 'Guide detail',
      },
      {
        locale: 'fa-IR',
        canonicalPath: '/guides/how-to-bypass-dpi-with-vless-reality',
        routeType: 'public',
      },
    );

    expect(metadata.alternates?.canonical).toBe(
      `${SITE_URL}/en-EN/guides/how-to-bypass-dpi-with-vless-reality`,
    );
    expect(metadata.robots).toMatchObject({
      index: false,
      follow: false,
    });
  });

  it('marks private routes as noindex without generating public alternates', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Login',
      },
      {
        locale: 'en-EN',
        canonicalPath: '/login',
      },
    );

    expect(metadata.alternates).toEqual({});
    expect(metadata.robots).toMatchObject({
      index: false,
      follow: false,
      googleBot: {
        index: false,
        follow: false,
      },
    });
  });

  it('auto-classifies dashboard-related client routes as private when canonicalPath is client-only', () => {
    const metadata = withSiteMetadata(
      {
        title: 'Analytics',
      },
      {
        locale: 'ru-RU',
        canonicalPath: '/analytics',
      },
    );

    expect(metadata.alternates).toEqual({});
    expect(metadata.robots).toMatchObject({
      index: false,
      follow: false,
    });
  });

  it('maps RTL locales to rtl direction and falls back to the default locale', () => {
    expect(getHtmlLanguageAttributes('ar-SA')).toEqual({
      lang: 'ar-SA',
      dir: 'rtl',
    });

    expect(getHtmlLanguageAttributes('ru-RU')).toEqual({
      lang: 'ru-RU',
      dir: 'ltr',
    });

    expect(getHtmlLanguageAttributes('unknown-locale')).toEqual({
      lang: 'en-EN',
      dir: 'ltr',
    });
  });
});
