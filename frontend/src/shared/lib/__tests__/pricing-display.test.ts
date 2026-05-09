import { describe, expect, it } from 'vitest';
import {
  formatMoney,
  getLocalDisplayEstimate,
  getPricePresentation,
  S1_BILLING_CURRENCY,
  S1_LOCAL_DISPLAY_RATE_VERSION,
} from '../pricing-display';

describe('pricing-display S1 currency rule', () => {
  it('keeps USD as the billing source of truth for every locale', () => {
    const price = getPricePresentation('ru-RU', {
      price_usd: 5.99,
      price_rub: 599,
    });

    expect(price.billing).toEqual({
      amount: 5.99,
      currency: S1_BILLING_CURRENCY,
    });
    expect(price.localEstimate).toMatchObject({
      amount: 600,
      currency: 'RUB',
      source: 'catalog',
      rateVersion: S1_LOCAL_DISPLAY_RATE_VERSION,
    });
  });

  it('derives a rounded-up RUB display estimate when catalog RUB is absent', () => {
    expect(getLocalDisplayEstimate('ru-RU', 8.99)).toEqual({
      amount: 900,
      currency: 'RUB',
      source: 'stage1_static_rate',
      rateVersion: S1_LOCAL_DISPLAY_RATE_VERSION,
    });
  });

  it('does not invent local currency estimates for unsupported locales', () => {
    const price = getPricePresentation('en-EN', {
      price_usd: 8.99,
      price_rub: 900,
    });

    expect(price.billing).toEqual({
      amount: 8.99,
      currency: S1_BILLING_CURRENCY,
    });
    expect(price.localEstimate).toBeNull();
  });

  it('formats currency with the provided ISO 4217 code', () => {
    expect(formatMoney('en-EN', 5.99, 'USD')).toBe('$5.99');
    expect(formatMoney('ru-RU', 600, 'RUB')).toContain('600');
  });
});
