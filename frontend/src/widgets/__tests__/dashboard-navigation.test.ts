import { describe, expect, it } from 'vitest';
import {
  DASHBOARD_NAV_ITEMS,
  DASHBOARD_NAV_LABEL_FALLBACKS,
} from '@/widgets/dashboard-navigation';

describe('dashboard navigation', () => {
  it('exposes only customer cabinet routes', () => {
    const hrefs = DASHBOARD_NAV_ITEMS.map((item) => item.href);

    expect(hrefs).toEqual([
      '/dashboard',
      '/servers',
      '/subscriptions',
      '/wallet',
      '/payment-history',
      '/support',
      '/messages',
      '/settings',
    ]);
  });

  it('keeps operator/admin routes out of the customer sidebar', () => {
    const hrefs = DASHBOARD_NAV_ITEMS.map((item) => item.href);

    expect(hrefs).not.toContain('/users');
    expect(hrefs).not.toContain('/partner');
    expect(hrefs).not.toContain('/analytics');
    expect(hrefs).not.toContain('/monitoring');
  });

  it('keeps settings last for mobile focus trapping', () => {
    expect(DASHBOARD_NAV_ITEMS.at(-1)?.href).toBe('/settings');
  });

  it('keeps customer-facing fallback labels readable', () => {
    expect(DASHBOARD_NAV_LABEL_FALLBACKS).toMatchObject({
      billing: 'Subscription',
      dashboard: 'Dashboard',
      paymentHistory: 'Payment history',
      referral: 'Referral rewards',
      servers: 'VPN servers',
      settings: 'Settings',
    });

    expect(Object.values(DASHBOARD_NAV_LABEL_FALLBACKS)).not.toEqual(
      expect.arrayContaining(['CABINET', 'CONFIG', 'NETWORK', 'ALERTS']),
    );
  });
});
