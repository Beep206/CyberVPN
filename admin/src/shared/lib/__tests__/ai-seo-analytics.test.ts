import { describe, expect, it } from 'vitest';
import {
  classifyAcquisitionSource,
  classifyCtaHref,
  getLocaleFromPathname,
  isAiAcquisitionSource,
  isAcquisitionRoute,
  pickUtmParams,
  resolveSeoCtaEventName,
} from '@/shared/lib/ai-seo-analytics';

describe('ai-seo-analytics', () => {
  it('classifies AI, search, and direct referrers', () => {
    expect(classifyAcquisitionSource('https://chatgpt.com/share/abc')).toMatchObject({
      sourceName: 'chatgpt',
      sourceType: 'ai',
    });

    expect(classifyAcquisitionSource('https://openai.com/index/something')).toMatchObject({
      sourceName: 'openai',
      sourceType: 'ai',
    });

    expect(classifyAcquisitionSource('https://www.google.com/search?q=vpn')).toMatchObject({
      sourceName: 'google',
      sourceType: 'search',
    });

    expect(classifyAcquisitionSource('https://search.brave.com/search?q=vpn')).toMatchObject({
      sourceName: 'brave',
      sourceType: 'search',
    });

    expect(classifyAcquisitionSource('')).toMatchObject({
      sourceName: 'direct',
      sourceType: 'direct',
    });
  });

  it('extracts locale-aware acquisition routes and CTA targets', () => {
    expect(getLocaleFromPathname('/ru-RU/pricing')).toBe('ru-RU');
    expect(isAcquisitionRoute('/ru-RU/pricing')).toBe(true);
    expect(isAcquisitionRoute('/ru-RU/dashboard')).toBe(false);
    expect(classifyCtaHref('/ru-RU/pricing', 'https://vpn.ozoxy.ru')).toBe('pricing');
    expect(classifyCtaHref('/ru-RU/contact', 'https://vpn.ozoxy.ru')).toBe('contact');
    expect(classifyCtaHref('https://t.me/cybervpn', 'https://vpn.ozoxy.ru')).toBe('telegram');
  });

  it('reads UTM parameters without leaking unrelated query params', () => {
    const utm = pickUtmParams(
      new URLSearchParams('utm_source=chatgpt&utm_medium=answer&utm_campaign=launch&utm_content=hero&utm_term=vpn&token=secret'),
    );

    expect(utm).toEqual({
      utmCampaign: 'launch',
      utmContent: 'hero',
      utmMedium: 'answer',
      utmSource: 'chatgpt',
      utmTerm: 'vpn',
    });
  });

  it('resolves truthful SEO acquisition events from CTA context', () => {
    expect(
      resolveSeoCtaEventName({
        pathname: '/ru-RU',
        ctaId: 'download',
        ctaZone: 'landing_hero',
      }),
    ).toBe('seo.landing_cta_click');
    expect(
      resolveSeoCtaEventName({
        pathname: '/ru-RU/features',
        ctaId: 'download',
        ctaZone: 'public_header',
      }),
    ).toBe('seo.download_cta_click');
    expect(
      resolveSeoCtaEventName({
        pathname: '/ru-RU/help',
        ctaId: 'contact',
        ctaZone: 'help_contact',
      }),
    ).toBe('seo.help_contact_click');
    expect(isAiAcquisitionSource(classifyAcquisitionSource('https://chatgpt.com/share/abc'))).toBe(
      true,
    );
  });
});
