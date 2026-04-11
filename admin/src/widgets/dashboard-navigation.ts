import { ADMIN_NAV_ITEMS } from '@/features/admin-shell/config/section-registry';

export const DASHBOARD_NAV_ITEMS = ADMIN_NAV_ITEMS;

export const dashboardNavigationItems = DASHBOARD_NAV_ITEMS;

export const DASHBOARD_NAV_LABEL_FALLBACKS = {
  adminConsole: 'ADMIN CONSOLE',
  closeMenu: 'Close menu',
  commerce: 'COMMERCE',
  commerceHint: 'Plans, payments, wallets',
  customers: 'CUSTOMERS',
  customersHint: 'Lifecycle, support, accounts',
  dashboard: 'DASHBOARD',
  dashboardHint: 'Health, queues, incidents',
  governance: 'GOVERNANCE',
  governanceHint: 'Audit, webhooks, staff access',
  growth: 'GROWTH',
  growthHint: 'Promo, invites, referrals',
  infrastructure: 'INFRASTRUCTURE',
  infrastructureHint: 'Servers, nodes, rollouts',
  integrations: 'INTEGRATIONS',
  integrationsHint: 'Telegram, push, realtime',
  mainNavigation: 'Main navigation',
  openMenu: 'Open menu',
  secureSession: 'SECURE SESSION',
  security: 'SECURITY',
  securityHint: 'Sessions, 2FA, trust',
  sidebar: 'Sidebar',
} as const;
