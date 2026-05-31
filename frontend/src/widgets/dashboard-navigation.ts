import {
  Activity,
  CreditCard,
  LifeBuoy,
  MessageSquare,
  Receipt,
  Server,
  Settings,
  UserPlus,
  Wallet,
} from 'lucide-react';
import { canStage1CustomerDashboardSurfaceAccess } from '@/shared/lib/stage1-customer-surface-policy';

const DASHBOARD_NAV_ITEM_CANDIDATES = [
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

export function getDashboardNavItems({ growthVisible = false } = {}) {
  return DASHBOARD_NAV_ITEM_CANDIDATES.filter((item) => {
    if (item.surface === 'referral') {
      return growthVisible;
    }

    return canStage1CustomerDashboardSurfaceAccess(item.surface);
  });
}

export const DASHBOARD_NAV_ITEMS = getDashboardNavItems({
  growthVisible: false,
});

export const dashboardNavigationItems = DASHBOARD_NAV_ITEMS;

export const DASHBOARD_NAV_LABEL_FALLBACKS = {
  billing: 'SUBSCRIPTION',
  closeMenu: 'Close menu',
  dashboard: 'CABINET',
  mainNavigation: 'Main navigation',
  messages: 'MESSAGES',
  openMenu: 'Open menu',
  paymentHistory: 'PAYMENTS',
  referral: 'REWARDS',
  servers: 'NETWORK',
  settings: 'SETTINGS',
  sidebar: 'Sidebar',
  support: 'SUPPORT',
  wallet: 'WALLET',
} as const;
