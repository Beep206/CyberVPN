import { describe, expect, it } from 'vitest';
import {
  LEGACY_ADMIN_ROUTE_RETIREMENTS,
  getRetiredLegacyAdminRouteTarget,
} from '../legacy-route-retirement';

describe('legacy admin route retirement', () => {
  it('maps legacy admin route families to canonical partner sections', () => {
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes')).toBe('/dashboard');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/commerce/payments')).toBe('/finance');
    expect(getRetiredLegacyAdminRouteTarget('/ru-RU/_legacy-admin-routes/customers/123')).toBe('/conversions');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/governance/admin-invites')).toBe('/team');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/governance/audit-log')).toBe('/compliance');
    expect(getRetiredLegacyAdminRouteTarget('/ru-RU/_legacy-admin-routes/growth/promo-codes')).toBe('/codes');
    expect(getRetiredLegacyAdminRouteTarget('/ru-RU/_legacy-admin-routes/growth/referrals')).toBe('/conversions');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/growth/partners')).toBe('/programs');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/infrastructure/servers')).toBe('/dashboard');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/integrations/telegram')).toBe('/integrations');
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/_legacy-admin-routes/security/two-factor')).toBe('/settings');
  });

  it('ignores canonical partner routes and unrelated unknown routes', () => {
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/dashboard')).toBeNull();
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/codes')).toBeNull();
    expect(getRetiredLegacyAdminRouteTarget('/en-EN/not-a-section')).toBeNull();
  });

  it('keeps every retirement target inside the canonical partner route set', () => {
    const canonicalTargets = new Set([
      '/dashboard',
      '/programs',
      '/codes',
      '/conversions',
      '/finance',
      '/team',
      '/compliance',
      '/integrations',
      '/settings',
    ]);

    for (const retirement of LEGACY_ADMIN_ROUTE_RETIREMENTS) {
      expect(canonicalTargets.has(retirement.targetPath)).toBe(true);
    }
  });
});
