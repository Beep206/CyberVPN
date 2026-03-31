import {
  Activity,
  BarChart3,
  CreditCard,
  Handshake,
  Receipt,
  Server,
  Settings,
  Shield,
  UserPlus,
  Users,
  Wallet,
} from 'lucide-react';

export const DASHBOARD_NAV_ITEMS = [
  { icon: Activity, labelKey: 'dashboard', href: '/dashboard' },
  { icon: Server, labelKey: 'servers', href: '/servers' },
  { icon: Users, labelKey: 'users', href: '/users' },
  { icon: CreditCard, labelKey: 'billing', href: '/subscriptions' },
  { icon: Wallet, labelKey: 'wallet', href: '/wallet' },
  { icon: Receipt, labelKey: 'paymentHistory', href: '/payment-history' },
  { icon: UserPlus, labelKey: 'referral', href: '/referral' },
  { icon: Handshake, labelKey: 'partner', href: '/partner' },
  { icon: BarChart3, labelKey: 'analytics', href: '/analytics' },
  { icon: Shield, labelKey: 'security', href: '/monitoring' },
  { icon: Settings, labelKey: 'settings', href: '/settings' },
] as const;

export const dashboardNavigationItems = DASHBOARD_NAV_ITEMS;

export const DASHBOARD_NAV_LABEL_FALLBACKS = {
  analytics: 'NET OP',
  billing: 'BILLING',
  closeMenu: 'Close menu',
  dashboard: 'DASHBOARD',
  mainNavigation: 'Main navigation',
  openMenu: 'Open menu',
  partner: 'PARTNER',
  paymentHistory: 'PAYMENTS',
  referral: 'REFERRAL',
  security: 'SECURITY',
  servers: 'SERVERS',
  settings: 'CONFIG',
  sidebar: 'Sidebar',
  users: 'CLIENTS',
  wallet: 'WALLET',
} as const;
