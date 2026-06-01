import { describe, expect, it } from 'vitest';
import {
  getDashboardNavItems,
  getMiniAppBottomNavItems,
  getMiniAppRewardsNavigationItems,
  getWebCabinetNavigationSections,
  hasAnyGrowthCapability,
  isCabinetRouteActive,
  isGrowthCapabilityEnabled,
  type CabinetNavigationCapabilities,
} from '@/shared/cabinet-navigation';
import { getStage1CustomerDashboardSurfacePolicy } from '@/shared/lib/stage1-customer-surface-policy';

const ALL_GROWTH_CAPABILITIES = {
  growth: {
    checkout_code_discounts: true,
    gift_codes: true,
    growth_hub: true,
    invites: true,
    promo_codes: true,
    referral: true,
  },
} as const satisfies CabinetNavigationCapabilities;

const DISABLED_GROWTH_CAPABILITIES = {
  growth: {
    checkout_code_discounts: false,
    gift_codes: false,
    growth_hub: false,
    invites: false,
    promo_codes: false,
    referral: false,
  },
} as const satisfies CabinetNavigationCapabilities;

describe('cabinet navigation foundation', () => {
  it('resolves target web sections in the frozen IA order', () => {
    const sections = getWebCabinetNavigationSections({
      capabilities: ALL_GROWTH_CAPABILITIES,
    });
    const sectionIds = sections.map((section) => section.id);

    expect(sectionIds.filter((id) => id !== 'communication')).toEqual([
      'main',
      'vpn',
      'billing',
      'growth',
      'account',
    ]);
    expect(sections.find((section) => section.id === 'growth')?.items).toHaveLength(
      6,
    );
  });

  it('keeps unavailable groups inspectable as hidden and disabled when requested', () => {
    const sections = getWebCabinetNavigationSections({
      capabilities: DISABLED_GROWTH_CAPABILITIES,
      includeDisabledItems: true,
      includeHiddenSections: true,
    });
    const growth = sections.find((section) => section.id === 'growth');

    expect(growth?.hidden).toBe(true);
    expect(growth?.items.map((item) => item.href)).toEqual([
      '/rewards',
      '/rewards/referral',
      '/rewards/gifts',
      '/rewards/invites',
      '/rewards/codes',
      '/rewards/notifications',
    ]);
    expect(growth?.items.every((item) => item.disabled)).toBe(true);
  });

  it('maps growth capabilities to reward subsections without exposing unavailable features', () => {
    const partialCapabilities = {
      growth: {
        checkout_code_discounts: false,
        gift_codes: false,
        growth_hub: false,
        invites: true,
        promo_codes: false,
        referral: true,
      },
    } as const satisfies CabinetNavigationCapabilities;

    const rewardsItems = getMiniAppRewardsNavigationItems({
      capabilities: partialCapabilities,
    });

    expect(rewardsItems.map((item) => item.id)).toEqual([
      'miniapp.rewards',
      'miniapp.rewards.referral',
      'miniapp.rewards.invites',
      'miniapp.rewards.codes',
    ]);
    expect(hasAnyGrowthCapability(DISABLED_GROWTH_CAPABILITIES)).toBe(false);
    expect(hasAnyGrowthCapability(partialCapabilities)).toBe(true);
    expect(isGrowthCapabilityEnabled(partialCapabilities, 'gift_codes')).toBe(
      false,
    );
  });

  it('keeps disabled reward items inspectable when requested', () => {
    const rewardsItems = getMiniAppRewardsNavigationItems({
      capabilities: DISABLED_GROWTH_CAPABILITIES,
      includeDisabledItems: true,
    });

    expect(rewardsItems).toHaveLength(6);
    expect(rewardsItems.every((item) => item.disabled)).toBe(true);
  });

  it('uses VPN as Mini App primary navigation and falls back to wallet only when rewards are unavailable', () => {
    const growthNav = getMiniAppBottomNavItems({
      capabilities: ALL_GROWTH_CAPABILITIES,
    });
    const fallbackNav = getMiniAppBottomNavItems({
      capabilities: DISABLED_GROWTH_CAPABILITIES,
    });

    expect(growthNav.map((item) => item.href)).toEqual([
      '/miniapp/home',
      '/miniapp/vpn',
      '/miniapp/plans',
      '/miniapp/rewards',
      '/miniapp/profile',
    ]);
    expect(fallbackNav.map((item) => item.href)).toEqual([
      '/miniapp/home',
      '/miniapp/vpn',
      '/miniapp/plans',
      '/miniapp/wallet',
      '/miniapp/profile',
    ]);
    expect(growthNav).toHaveLength(5);
    expect(fallbackNav).toHaveLength(5);
  });

  it('matches active routes exactly while allowing nested route segments and legacy aliases', () => {
    expect(isCabinetRouteActive('/servers', '/servers')).toBe(true);
    expect(isCabinetRouteActive('/servers/eu-west', '/servers')).toBe(true);
    expect(isCabinetRouteActive('/server-status', '/servers')).toBe(false);
    expect(
      isCabinetRouteActive('/en-EN/miniapp/rewards/gifts', '/miniapp/rewards'),
    ).toBe(true);
    expect(
      isCabinetRouteActive('/miniapp/rewards-gifts', '/miniapp/rewards'),
    ).toBe(false);
    expect(
      isCabinetRouteActive('/miniapp/referral', '/miniapp/rewards', {
        aliases: ['/miniapp/referral'],
      }),
    ).toBe(true);
    expect(
      isCabinetRouteActive('/miniapp/referral/history', '/miniapp/rewards', {
        aliases: ['/miniapp/referral'],
      }),
    ).toBe(false);
  });

  it('preserves the legacy dashboard flatten helper for current sidebar consumers', () => {
    const defaultItems = getDashboardNavItems();
    const growthItems = getDashboardNavItems({ growthVisible: true });
    const supportRoutes = getStage1CustomerDashboardSurfacePolicy().support
      ? ['/support', '/messages']
      : [];

    expect(defaultItems.map((item) => item.href)).toEqual([
      '/dashboard',
      '/servers',
      '/subscriptions',
      '/wallet',
      '/payment-history',
      ...supportRoutes,
      '/settings',
    ]);
    expect(growthItems.map((item) => item.href)).toEqual([
      '/dashboard',
      '/servers',
      '/subscriptions',
      '/wallet',
      '/payment-history',
      '/referral',
      ...supportRoutes,
      '/settings',
    ]);
    expect(growthItems.map((item) => item.href)).not.toContain('/rewards');
    expect(growthItems.at(-1)?.href).toBe('/settings');
    expect(growthItems[1]?.match('/servers-sidecar')).toBe(false);
  });
});
