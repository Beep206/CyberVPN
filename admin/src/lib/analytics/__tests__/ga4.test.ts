import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createGa4Provider } from '@/lib/analytics/providers/ga4';

describe('GA4 analytics provider', () => {
  beforeEach(() => {
    window.gtag = undefined;
  });

  it('normalizes SEO events and parameters for gtag', () => {
    const gtag = vi.fn();
    window.gtag = gtag;
    const provider = createGa4Provider('G-TEST123');

    provider.track('seo.landing_cta_click', {
      ctaId: 'download',
      ctaZone: 'landing_hero',
      reducedMotion: true,
      sourceName: 'chatgpt',
      timestamp: 123,
    });

    expect(gtag).toHaveBeenCalledWith(
      'event',
      'seo_landing_cta_click',
      expect.objectContaining({
        cta_id: 'download',
        cta_zone: 'landing_hero',
        reduced_motion: 'true',
        source_name: 'chatgpt',
        timestamp: 123,
      }),
    );
  });

  it('maps identify and reset calls to GA4 config commands', () => {
    const gtag = vi.fn();
    window.gtag = gtag;
    const provider = createGa4Provider('G-TEST123');

    provider.identify('user-42', { planTier: 'elite_sync' });
    provider.reset();

    expect(gtag).toHaveBeenCalledWith('config', 'G-TEST123', { user_id: 'user-42' });
    expect(gtag).toHaveBeenCalledWith(
      'set',
      'user_properties',
      expect.objectContaining({ plan_tier: 'elite_sync' }),
    );
    expect(gtag).toHaveBeenCalledWith('config', 'G-TEST123', { user_id: null });
  });

  it('stays inert when gtag is unavailable', () => {
    const provider = createGa4Provider('G-TEST123');

    expect(() => provider.track('seo.download_cta_click', { ctaId: 'download' })).not.toThrow();
    expect(() => provider.identify('user-42')).not.toThrow();
    expect(() => provider.reset()).not.toThrow();
  });
});
