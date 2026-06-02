import {
  Activity,
  Bell,
  CreditCard,
  Gift,
  Home,
  KeyRound,
  LifeBuoy,
  MessageSquare,
  Receipt,
  Server,
  Settings,
  ShieldCheck,
  Tags,
  User,
  UserPlus,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import {
  getStage1CustomerDashboardSurfacePolicy,
  type Stage1CustomerDashboardSurface,
} from '@/shared/lib/stage1-customer-surface-policy';

export type CabinetNavigationSectionId =
  | 'account'
  | 'billing'
  | 'communication'
  | 'growth'
  | 'main'
  | 'vpn';

export type CabinetNavigationItemId =
  | 'miniapp.home'
  | 'miniapp.plans'
  | 'miniapp.profile'
  | 'miniapp.rewards'
  | 'miniapp.rewards.codes'
  | 'miniapp.rewards.gifts'
  | 'miniapp.rewards.invites'
  | 'miniapp.rewards.notifications'
  | 'miniapp.rewards.referral'
  | 'miniapp.vpn'
  | 'miniapp.wallet'
  | 'web.dashboard'
  | 'web.messages'
  | 'web.paymentHistory'
  | 'web.rewards'
  | 'web.rewards.codes'
  | 'web.rewards.gifts'
  | 'web.rewards.invites'
  | 'web.rewards.notifications'
  | 'web.rewards.referral'
  | 'web.servers'
  | 'web.settings'
  | 'web.subscriptions'
  | 'web.support'
  | 'web.wallet';

export type CabinetGrowthCapabilityKey =
  | 'checkout_code_discounts'
  | 'gift_codes'
  | 'growth_hub'
  | 'invites'
  | 'promo_codes'
  | 'referral';

export type DashboardNavigationLabelKey =
  | 'billing'
  | 'dashboard'
  | 'messages'
  | 'paymentHistory'
  | 'referral'
  | 'servers'
  | 'settings'
  | 'support'
  | 'wallet';

export type DashboardCompatibilitySurface =
  | Stage1CustomerDashboardSurface
  | 'support';

export interface CabinetGrowthCapabilities {
  checkout_code_discounts?: boolean;
  gift_codes?: boolean;
  growth_hub?: boolean;
  invites?: boolean;
  promo_codes?: boolean;
  referral?: boolean;
}

export interface CabinetNavigationCapabilities {
  growth?: CabinetGrowthCapabilities;
}

export interface CabinetNavigationItem {
  disabled: boolean;
  href: string;
  icon: LucideIcon;
  id: CabinetNavigationItemId;
  labelKey: string;
  legacyHrefs: readonly string[];
  match: (pathname: string | null | undefined) => boolean;
}

export interface CabinetNavigationSection {
  hidden: boolean;
  id: CabinetNavigationSectionId;
  items: readonly CabinetNavigationItem[];
  labelKey: string;
}

export interface DashboardNavigationItem {
  disabled?: boolean;
  href: string;
  icon: LucideIcon;
  labelKey: DashboardNavigationLabelKey;
  match: (pathname: string | null | undefined) => boolean;
  surface: DashboardCompatibilitySurface;
}

export interface CabinetNavigationResolveOptions {
  capabilities?: CabinetNavigationCapabilities;
  growthVisible?: boolean;
  includeDisabledItems?: boolean;
  includeHiddenSections?: boolean;
}

type CapabilityRequirement =
  | { anyGrowth: true }
  | { anyOf: readonly CabinetGrowthCapabilityKey[] };

interface CabinetNavigationItemDefinition {
  disabled?: boolean;
  href: string;
  icon: LucideIcon;
  id: CabinetNavigationItemId;
  labelKey: string;
  legacyHrefs?: readonly string[];
  requirement?: CapabilityRequirement;
  surface?: DashboardCompatibilitySurface;
}

interface CabinetNavigationSectionDefinition {
  hidden?: boolean;
  id: CabinetNavigationSectionId;
  items: readonly CabinetNavigationItemDefinition[];
  labelKey: string;
  requirement?: CapabilityRequirement;
}

interface DashboardNavigationItemDefinition {
  href: string;
  icon: LucideIcon;
  labelKey: DashboardNavigationLabelKey;
  requirement?: CapabilityRequirement;
  surface: DashboardCompatibilitySurface;
}

const GROWTH_CAPABILITY_KEYS = [
  'checkout_code_discounts',
  'gift_codes',
  'growth_hub',
  'invites',
  'promo_codes',
  'referral',
] as const satisfies readonly CabinetGrowthCapabilityKey[];

const ANY_GROWTH_REQUIREMENT = { anyGrowth: true } as const;
const REFERRAL_REQUIREMENT = {
  anyOf: ['growth_hub', 'referral'],
} as const satisfies CapabilityRequirement;
const GIFTS_REQUIREMENT = {
  anyOf: ['gift_codes', 'growth_hub'],
} as const satisfies CapabilityRequirement;
const INVITES_REQUIREMENT = {
  anyOf: ['growth_hub', 'invites'],
} as const satisfies CapabilityRequirement;
const CODES_REQUIREMENT = {
  anyOf: [
    'checkout_code_discounts',
    'gift_codes',
    'growth_hub',
    'invites',
    'promo_codes',
  ],
} as const satisfies CapabilityRequirement;
const NOTIFICATIONS_REQUIREMENT = {
  anyOf: ['growth_hub'],
} as const satisfies CapabilityRequirement;

const WEB_CABINET_SECTION_DEFINITIONS: readonly CabinetNavigationSectionDefinition[] = [
  {
    id: 'main',
    labelKey: 'sections.main',
    items: [
      {
        id: 'web.dashboard',
        href: '/dashboard',
        icon: Activity,
        labelKey: 'items.overview',
      },
    ],
  },
  {
    id: 'vpn',
    labelKey: 'sections.vpn',
    items: [
      {
        id: 'web.servers',
        href: '/servers',
        icon: Server,
        labelKey: 'items.vpnAccess',
      },
      {
        id: 'web.subscriptions',
        href: '/subscriptions',
        icon: CreditCard,
        labelKey: 'items.subscription',
      },
    ],
  },
  {
    id: 'billing',
    labelKey: 'sections.billing',
    items: [
      {
        id: 'web.wallet',
        href: '/wallet',
        icon: Wallet,
        labelKey: 'items.wallet',
      },
      {
        id: 'web.paymentHistory',
        href: '/payment-history',
        icon: Receipt,
        labelKey: 'items.paymentHistory',
      },
    ],
  },
  {
    id: 'growth',
    labelKey: 'sections.growth',
    items: [
      {
        id: 'web.rewards',
        href: '/rewards',
        icon: Gift,
        labelKey: 'items.rewards',
        legacyHrefs: ['/referral'],
        requirement: ANY_GROWTH_REQUIREMENT,
      },
      {
        id: 'web.rewards.referral',
        href: '/rewards/referral',
        icon: UserPlus,
        labelKey: 'items.referral',
        legacyHrefs: ['/referral'],
        requirement: REFERRAL_REQUIREMENT,
      },
      {
        id: 'web.rewards.gifts',
        href: '/rewards/gifts',
        icon: Gift,
        labelKey: 'items.gifts',
        requirement: GIFTS_REQUIREMENT,
      },
      {
        id: 'web.rewards.invites',
        href: '/rewards/invites',
        icon: UserPlus,
        labelKey: 'items.invites',
        requirement: INVITES_REQUIREMENT,
      },
      {
        id: 'web.rewards.codes',
        href: '/rewards/codes',
        icon: Tags,
        labelKey: 'items.codes',
        requirement: CODES_REQUIREMENT,
      },
      {
        id: 'web.rewards.notifications',
        href: '/rewards/notifications',
        icon: Bell,
        labelKey: 'items.rewardNotifications',
        requirement: NOTIFICATIONS_REQUIREMENT,
      },
    ],
  },
  {
    id: 'communication',
    labelKey: 'sections.communication',
    items: [
      {
        id: 'web.support',
        href: '/support',
        icon: LifeBuoy,
        labelKey: 'items.support',
        surface: 'support',
      },
      {
        id: 'web.messages',
        href: '/messages',
        icon: MessageSquare,
        labelKey: 'items.messages',
        surface: 'support',
      },
    ],
  },
  {
    id: 'account',
    labelKey: 'sections.account',
    items: [
      {
        id: 'web.settings',
        href: '/settings',
        icon: Settings,
        labelKey: 'items.profileSecurity',
      },
    ],
  },
] as const;

const MINI_APP_BOTTOM_NAV_WITH_REWARDS: readonly CabinetNavigationItemDefinition[] = [
  {
    id: 'miniapp.home',
    href: '/miniapp/home',
    icon: Home,
    labelKey: 'nav.home',
    legacyHrefs: ['/miniapp', '/miniapp/'],
  },
  {
    id: 'miniapp.vpn',
    href: '/miniapp/vpn',
    icon: ShieldCheck,
    labelKey: 'nav.vpn',
  },
  {
    id: 'miniapp.plans',
    href: '/miniapp/plans',
    icon: CreditCard,
    labelKey: 'nav.plans',
  },
  {
    id: 'miniapp.rewards',
    href: '/miniapp/rewards',
    icon: Gift,
    labelKey: 'nav.rewards',
    legacyHrefs: ['/miniapp/referral'],
    requirement: ANY_GROWTH_REQUIREMENT,
  },
  {
    id: 'miniapp.profile',
    href: '/miniapp/profile',
    icon: User,
    labelKey: 'nav.profile',
  },
] as const;

const MINI_APP_BOTTOM_NAV_FALLBACK: readonly CabinetNavigationItemDefinition[] = [
  MINI_APP_BOTTOM_NAV_WITH_REWARDS[0],
  MINI_APP_BOTTOM_NAV_WITH_REWARDS[1],
  MINI_APP_BOTTOM_NAV_WITH_REWARDS[2],
  {
    id: 'miniapp.wallet',
    href: '/miniapp/wallet',
    icon: Wallet,
    labelKey: 'nav.wallet',
  },
  MINI_APP_BOTTOM_NAV_WITH_REWARDS[4],
] as const;

const MINI_APP_REWARDS_NAV_DEFINITIONS: readonly CabinetNavigationItemDefinition[] = [
  {
    id: 'miniapp.rewards',
    href: '/miniapp/rewards',
    icon: Gift,
    labelKey: 'rewards.overview',
    legacyHrefs: ['/miniapp/referral'],
    requirement: ANY_GROWTH_REQUIREMENT,
  },
  {
    id: 'miniapp.rewards.referral',
    href: '/miniapp/rewards/referral',
    icon: UserPlus,
    labelKey: 'rewards.referral',
    legacyHrefs: ['/miniapp/referral'],
    requirement: REFERRAL_REQUIREMENT,
  },
  {
    id: 'miniapp.rewards.gifts',
    href: '/miniapp/rewards/gifts',
    icon: Gift,
    labelKey: 'rewards.gifts',
    requirement: GIFTS_REQUIREMENT,
  },
  {
    id: 'miniapp.rewards.invites',
    href: '/miniapp/rewards/invites',
    icon: UserPlus,
    labelKey: 'rewards.invites',
    requirement: INVITES_REQUIREMENT,
  },
  {
    id: 'miniapp.rewards.codes',
    href: '/miniapp/rewards/codes',
    icon: KeyRound,
    labelKey: 'rewards.codes',
    requirement: CODES_REQUIREMENT,
  },
  {
    id: 'miniapp.rewards.notifications',
    href: '/miniapp/rewards/notifications',
    icon: Bell,
    labelKey: 'rewards.notifications',
    requirement: NOTIFICATIONS_REQUIREMENT,
  },
] as const;

const DASHBOARD_COMPATIBILITY_ITEM_DEFINITIONS: readonly DashboardNavigationItemDefinition[] = [
  {
    icon: Activity,
    labelKey: 'dashboard',
    href: '/dashboard',
    surface: 'dashboard',
  },
  { icon: Server, labelKey: 'servers', href: '/servers', surface: 'servers' },
  {
    icon: CreditCard,
    labelKey: 'billing',
    href: '/subscriptions',
    surface: 'subscriptions',
  },
  { icon: Wallet, labelKey: 'wallet', href: '/wallet', surface: 'wallet' },
  {
    icon: Receipt,
    labelKey: 'paymentHistory',
    href: '/payment-history',
    surface: 'paymentHistory',
  },
  {
    icon: UserPlus,
    labelKey: 'referral',
    href: '/referral',
    requirement: ANY_GROWTH_REQUIREMENT,
    surface: 'referral',
  },
  {
    icon: LifeBuoy,
    labelKey: 'support',
    href: '/support',
    surface: 'support',
  },
  {
    icon: MessageSquare,
    labelKey: 'messages',
    href: '/messages',
    surface: 'support',
  },
  {
    icon: Settings,
    labelKey: 'settings',
    href: '/settings',
    surface: 'settings',
  },
] as const;

export const DASHBOARD_NAV_LABEL_FALLBACKS = {
  billing: 'Subscription',
  closeMenu: 'Close menu',
  dashboard: 'Dashboard',
  mainNavigation: 'Main navigation',
  messages: 'Messages',
  openMenu: 'Open menu',
  paymentHistory: 'Payment history',
  referral: 'Referral rewards',
  servers: 'VPN servers',
  settings: 'Settings',
  sidebar: 'Sidebar',
  support: 'Support',
  wallet: 'Wallet',
} as const;

export const CABINET_NAV_LABEL_FALLBACKS = {
  ...DASHBOARD_NAV_LABEL_FALLBACKS,
  'items.codes': 'CODES',
  'items.gifts': 'GIFTS',
  'items.invites': 'INVITES',
  'items.messages': 'MESSAGES',
  'items.overview': 'CABINET',
  'items.paymentHistory': 'PAYMENTS',
  'items.profileSecurity': 'CONFIG',
  'items.referral': 'REFERRAL',
  'items.rewardNotifications': 'ALERTS',
  'items.rewards': 'REWARDS HUB',
  'items.subscription': 'SUBSCRIPTION',
  'items.support': 'SUPPORT',
  'items.vpnAccess': 'NETWORK',
  'items.wallet': 'WALLET',
  'sections.account': 'ACCOUNT',
  'sections.billing': 'BILLING',
  'sections.communication': 'SUPPORT',
  'sections.growth': 'REWARDS',
  'sections.main': 'MAIN',
  'sections.vpn': 'VPN',
} as const;

export function getCabinetNavigationLabelFallback(labelKey: string): string {
  return (
    CABINET_NAV_LABEL_FALLBACKS[
      labelKey as keyof typeof CABINET_NAV_LABEL_FALLBACKS
    ] ?? labelKey
  );
}

function canDashboardCompatibilitySurfaceAccess(
  surface: DashboardCompatibilitySurface | undefined,
): boolean {
  if (!surface) {
    return true;
  }

  const policy = getStage1CustomerDashboardSurfacePolicy() as Record<
    string,
    boolean | undefined
  >;

  return policy[surface] === true;
}

function hasCapabilityRequirement(
  requirement: CapabilityRequirement | undefined,
  options: CabinetNavigationResolveOptions,
): boolean {
  if (!requirement) {
    return true;
  }

  if ('anyGrowth' in requirement) {
    return options.growthVisible ?? hasAnyGrowthCapability(options.capabilities);
  }

  if (options.capabilities?.growth) {
    return requirement.anyOf.some((key) =>
      isGrowthCapabilityEnabled(options.capabilities, key),
    );
  }

  return options.growthVisible === true;
}

function resolveItem(
  item: CabinetNavigationItemDefinition,
  options: CabinetNavigationResolveOptions,
): CabinetNavigationItem | null {
  const capabilityEnabled = hasCapabilityRequirement(item.requirement, options);
  const surfaceEnabled = canDashboardCompatibilitySurfaceAccess(item.surface);
  const disabled = item.disabled === true || !capabilityEnabled || !surfaceEnabled;

  if (disabled && options.includeDisabledItems !== true) {
    return null;
  }

  return {
    disabled,
    href: item.href,
    icon: item.icon,
    id: item.id,
    labelKey: item.labelKey,
    legacyHrefs: item.legacyHrefs ?? [],
    match: (pathname) =>
      isCabinetRouteActive(pathname, item.href, {
        aliases: item.legacyHrefs,
      }),
  };
}

function resolveItems(
  items: readonly CabinetNavigationItemDefinition[],
  options: CabinetNavigationResolveOptions,
): CabinetNavigationItem[] {
  return items.flatMap((item) => {
    const resolved = resolveItem(item, options);
    return resolved ? [resolved] : [];
  });
}

function normalizeCabinetPath(pathname: string): string {
  const withoutHash = pathname.split('#', 1)[0] ?? pathname;
  const withoutQuery = withoutHash.split('?', 1)[0] ?? withoutHash;
  const withLeadingSlash = withoutQuery.startsWith('/')
    ? withoutQuery
    : `/${withoutQuery}`;
  const withoutLocale = withLeadingSlash.replace(
    /^\/[a-z]{2,3}-[A-Z]{2}(?=\/|$)/,
    '',
  );
  const normalized = withoutLocale || '/';

  if (normalized.length > 1 && normalized.endsWith('/')) {
    return normalized.slice(0, -1);
  }

  return normalized;
}

function isPathActiveForHref(pathname: string, href: string): boolean {
  const normalizedPath = normalizeCabinetPath(pathname);
  const normalizedHref = normalizeCabinetPath(href);

  return (
    normalizedPath === normalizedHref ||
    normalizedPath.startsWith(`${normalizedHref}/`)
  );
}

export function isGrowthCapabilityEnabled(
  capabilities: CabinetNavigationCapabilities | undefined,
  capability: CabinetGrowthCapabilityKey,
): boolean {
  return capabilities?.growth?.[capability] === true;
}

export function hasAnyGrowthCapability(
  capabilities: CabinetNavigationCapabilities | undefined,
): boolean {
  return GROWTH_CAPABILITY_KEYS.some((key) =>
    isGrowthCapabilityEnabled(capabilities, key),
  );
}

export function isCabinetRouteActive(
  pathname: string | null | undefined,
  href: string,
  options: { aliases?: readonly string[] } = {},
): boolean {
  if (!pathname) {
    return false;
  }

  if (isPathActiveForHref(pathname, href)) {
    return true;
  }

  const normalizedPath = normalizeCabinetPath(pathname);
  return (options.aliases ?? []).some(
    (alias) => normalizedPath === normalizeCabinetPath(alias),
  );
}

export function getWebCabinetNavigationSections(
  options: CabinetNavigationResolveOptions = {},
): CabinetNavigationSection[] {
  return WEB_CABINET_SECTION_DEFINITIONS.flatMap((section) => {
    if (section.hidden === true && options.includeHiddenSections !== true) {
      return [];
    }

    if (!hasCapabilityRequirement(section.requirement, options)) {
      return [];
    }

    const items = resolveItems(section.items, options);
    const hidden =
      section.hidden === true ||
      items.length === 0 ||
      items.every((item) => item.disabled);

    if (hidden && options.includeHiddenSections !== true) {
      return [];
    }

    return [
      {
        hidden,
        id: section.id,
        items,
        labelKey: section.labelKey,
      },
    ];
  });
}

export function getMiniAppBottomNavItems(
  options: CabinetNavigationResolveOptions = {},
): CabinetNavigationItem[] {
  const growthVisible =
    options.growthVisible ?? hasAnyGrowthCapability(options.capabilities);
  const definitions = growthVisible
    ? MINI_APP_BOTTOM_NAV_WITH_REWARDS
    : MINI_APP_BOTTOM_NAV_FALLBACK;

  return resolveItems(definitions, {
    ...options,
    growthVisible,
  });
}

export function getMiniAppRewardsNavigationItems(
  options: CabinetNavigationResolveOptions = {},
): CabinetNavigationItem[] {
  return resolveItems(MINI_APP_REWARDS_NAV_DEFINITIONS, options);
}

export function getDashboardNavItems({
  growthVisible = false,
}: { growthVisible?: boolean } = {}): DashboardNavigationItem[] {
  return DASHBOARD_COMPATIBILITY_ITEM_DEFINITIONS.flatMap((item) => {
    if (!canDashboardCompatibilitySurfaceAccess(item.surface)) {
      return [];
    }

    if (!hasCapabilityRequirement(item.requirement, { growthVisible })) {
      return [];
    }

    return [
      {
        disabled: false,
        href: item.href,
        icon: item.icon,
        labelKey: item.labelKey,
        match: (pathname) => isCabinetRouteActive(pathname, item.href),
        surface: item.surface,
      },
    ];
  });
}

export const DASHBOARD_NAV_ITEMS = getDashboardNavItems({
  growthVisible: false,
});

export const dashboardNavigationItems = DASHBOARD_NAV_ITEMS;
