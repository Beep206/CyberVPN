import {
  Activity,
  CreditCard,
  Receipt,
  Server,
  Settings,
  UserPlus,
  Wallet,
} from 'lucide-react';

export const DASHBOARD_NAV_ITEMS = [
  { icon: Activity, labelKey: 'dashboard', href: '/dashboard' },
  { icon: Server, labelKey: 'servers', href: '/servers' },
  { icon: CreditCard, labelKey: 'billing', href: '/subscriptions' },
  { icon: Wallet, labelKey: 'wallet', href: '/wallet' },
  { icon: Receipt, labelKey: 'paymentHistory', href: '/payment-history' },
  { icon: UserPlus, labelKey: 'referral', href: '/referral' },
  { icon: Settings, labelKey: 'settings', href: '/settings' },
] as const;

export const dashboardNavigationItems = DASHBOARD_NAV_ITEMS;

export const DASHBOARD_NAV_LABEL_FALLBACKS = {
  billing: 'SUBSCRIPTION',
  closeMenu: 'Close menu',
  dashboard: 'CABINET',
  mainNavigation: 'Main navigation',
  openMenu: 'Open menu',
  paymentHistory: 'PAYMENTS',
  referral: 'REWARDS',
  servers: 'NETWORK',
  settings: 'SETTINGS',
  sidebar: 'Sidebar',
  wallet: 'WALLET',
} as const;
