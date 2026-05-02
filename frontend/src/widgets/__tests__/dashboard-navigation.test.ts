import { describe, expect, it } from 'vitest';
import { DASHBOARD_NAV_ITEMS } from '@/widgets/dashboard-navigation';

describe('dashboard navigation', () => {
  it('exposes only customer cabinet routes', () => {
    const hrefs = DASHBOARD_NAV_ITEMS.map((item) => item.href);

    expect(hrefs).toEqual([
      '/dashboard',
      '/servers',
      '/subscriptions',
      '/wallet',
      '/payment-history',
      '/referral',
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
});
