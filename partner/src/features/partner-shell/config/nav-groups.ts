import type {
  PartnerNavItem,
  PartnerSectionSlug,
} from '@/features/partner-shell/config/section-registry';
import { PARTNER_NAV_ITEMS } from '@/features/partner-shell/config/section-registry';
import type { PartnerRouteKey } from '@/features/partner-portal-state/lib/portal-visibility';

export type PartnerNavGroupId =
  | 'main'
  | 'onboarding'
  | 'workspace'
  | 'promotion'
  | 'results'
  | 'finance'
  | 'control'
  | 'technical';

export type PartnerNavGroupLabelKey =
  | 'groupMain'
  | 'groupOnboarding'
  | 'groupWorkspace'
  | 'groupPromotion'
  | 'groupResults'
  | 'groupFinance'
  | 'groupControl'
  | 'groupTechnical';

export type PartnerNavGroupHintKey =
  | 'groupMainHint'
  | 'groupOnboardingHint'
  | 'groupWorkspaceHint'
  | 'groupPromotionHint'
  | 'groupResultsHint'
  | 'groupFinanceHint'
  | 'groupControlHint'
  | 'groupTechnicalHint';

export type PartnerNavGroupConfig = {
  id: PartnerNavGroupId;
  labelKey: PartnerNavGroupLabelKey;
  hintKey: PartnerNavGroupHintKey;
  routes: readonly PartnerRouteKey[];
};

export const PARTNER_NAV_GROUPS = [
  {
    id: 'main',
    labelKey: 'groupMain',
    hintKey: 'groupMainHint',
    routes: ['dashboard', 'notifications'],
  },
  {
    id: 'onboarding',
    labelKey: 'groupOnboarding',
    hintKey: 'groupOnboardingHint',
    routes: ['application', 'organization', 'legal'],
  },
  {
    id: 'workspace',
    labelKey: 'groupWorkspace',
    hintKey: 'groupWorkspaceHint',
    routes: ['team', 'settings'],
  },
  {
    id: 'promotion',
    labelKey: 'groupPromotion',
    hintKey: 'groupPromotionHint',
    routes: ['programs', 'codes', 'campaigns'],
  },
  {
    id: 'results',
    labelKey: 'groupResults',
    hintKey: 'groupResultsHint',
    routes: ['conversions', 'analytics'],
  },
  {
    id: 'finance',
    labelKey: 'groupFinance',
    hintKey: 'groupFinanceHint',
    routes: ['finance'],
  },
  {
    id: 'control',
    labelKey: 'groupControl',
    hintKey: 'groupControlHint',
    routes: ['compliance', 'cases'],
  },
  {
    id: 'technical',
    labelKey: 'groupTechnical',
    hintKey: 'groupTechnicalHint',
    routes: ['integrations', 'reseller'],
  },
] as const satisfies readonly PartnerNavGroupConfig[];

export function getPartnerRouteFromNavItem(item: PartnerNavItem): PartnerRouteKey {
  return item.href === '/dashboard' ? 'dashboard' : item.href.slice(1) as PartnerSectionSlug;
}

export function getPartnerNavItemByRoute(route: PartnerRouteKey): PartnerNavItem {
  const href = route === 'dashboard' ? '/dashboard' : `/${route}`;
  const item = PARTNER_NAV_ITEMS.find((navItem) => navItem.href === href);

  if (!item) {
    throw new Error(`Missing partner nav item for route: ${route}`);
  }

  return item;
}
