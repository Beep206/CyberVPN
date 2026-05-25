import { describe, expect, it } from 'vitest';
import {
  formatMoney,
  getLocalDisplayEstimate,
  getPricePresentation,
  S2_DISPLAY_RATE_VERSION,
} from '../pricing-display';

describe('pricing-display S2 currency rule', () => {
  it('uses the locale default display currency for pricing', () => {
    const price = getPricePresentation('ru-RU', {
      price_usd: 5.99,
      price_rub: 599,
    });

    expect(price.billing).toEqual({
      amount: 600,
      currency: 'RUB',
    });
    expect(price.localEstimate).toMatchObject({
      amount: 600,
      currency: 'RUB',
      source: 'catalog',
      rateVersion: S2_DISPLAY_RATE_VERSION,
    });
  });

  it('derives a rounded-up RUB display estimate when catalog RUB is absent', () => {
    expect(getLocalDisplayEstimate('ru-RU', 8.99)).toEqual({
      amount: 900,
      currency: 'RUB',
      source: 's2_static_rate',
      rateVersion: S2_DISPLAY_RATE_VERSION,
    });
  });

  it('supports explicit currency override independent from locale', () => {
    const price = getPricePresentation('en-EN', {
      price_usd: 8.99,
      price_rub: 900,
    }, 'KZT');

    expect(price.billing).toEqual({
      amount: 4050,
      currency: 'KZT',
    });
    expect(price.localEstimate).toMatchObject({
      amount: 4050,
      currency: 'KZT',
      source: 's2_static_rate',
      rateVersion: S2_DISPLAY_RATE_VERSION,
    });
  });

  it('falls back to USD for unsupported locales and currency overrides', () => {
    const price = getPricePresentation('en-EN', {
      price_usd: 8.99,
      price_rub: 900,
    }, 'NOT_REAL');

    expect(price.billing).toEqual({
      amount: 8.99,
      currency: 'USD',
    });
    expect(price.localEstimate).toMatchObject({
      amount: 8.99,
      currency: 'USD',
      source: 's2_static_rate',
      rateVersion: S2_DISPLAY_RATE_VERSION,
    });
  });

  it('formats currency with the provided ISO 4217 code', () => {
    expect(formatMoney('en-EN', 5.99, 'USD')).toBe('$5.99');
    expect(formatMoney('ru-RU', 600, 'RUB')).toContain('600');
  });
});
