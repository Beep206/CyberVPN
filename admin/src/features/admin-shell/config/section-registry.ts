import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Bot,
  ChartColumnIncreasing,
  Landmark,
  ScrollText,
  Shield,
  Users,
  Waypoints,
} from 'lucide-react';

export const ADMIN_SECTION_SLUGS = [
  'customers',
  'commerce',
  'growth',
  'infrastructure',
  'security',
  'governance',
  'integrations',
] as const;

export type AdminSectionSlug = (typeof ADMIN_SECTION_SLUGS)[number];

export interface AdminNavItem {
  href: '/dashboard' | `/${AdminSectionSlug}`;
  icon: LucideIcon;
  labelKey:
    | 'dashboard'
    | 'customers'
    | 'commerce'
    | 'growth'
    | 'infrastructure'
    | 'security'
    | 'governance'
    | 'integrations';
  hintKey:
    | 'dashboardHint'
    | 'customersHint'
    | 'commerceHint'
    | 'growthHint'
    | 'infrastructureHint'
    | 'securityHint'
    | 'governanceHint'
    | 'integrationsHint';
}

export const ADMIN_NAV_ITEMS: readonly AdminNavItem[] = [
  {
    href: '/dashboard',
    icon: Activity,
    labelKey: 'dashboard',
    hintKey: 'dashboardHint',
  },
  {
    href: '/customers',
    icon: Users,
    labelKey: 'customers',
    hintKey: 'customersHint',
  },
  {
    href: '/commerce',
    icon: Landmark,
    labelKey: 'commerce',
    hintKey: 'commerceHint',
  },
  {
    href: '/growth',
    icon: ChartColumnIncreasing,
    labelKey: 'growth',
    hintKey: 'growthHint',
  },
  {
    href: '/infrastructure',
    icon: Waypoints,
    labelKey: 'infrastructure',
    hintKey: 'infrastructureHint',
  },
  {
    href: '/security',
    icon: Shield,
    labelKey: 'security',
    hintKey: 'securityHint',
  },
  {
    href: '/governance',
    icon: ScrollText,
    labelKey: 'governance',
    hintKey: 'governanceHint',
  },
  {
    href: '/integrations',
    icon: Bot,
    labelKey: 'integrations',
    hintKey: 'integrationsHint',
  },
] as const;

export interface AdminSectionOverviewConfig {
  slug: AdminSectionSlug;
  readinessTone: 'strong' | 'partial' | 'blocked';
  availableNow: readonly string[];
  nextModules: readonly string[];
}

export const ADMIN_SECTION_OVERVIEWS: Record<
  AdminSectionSlug,
  AdminSectionOverviewConfig
> = {
  customers: {
    slug: 'customers',
    readinessTone: 'partial',
    availableNow: [
      'customerDirectory',
      'customerDetail',
      'walletTopups',
      'partnerPromotions',
    ],
    nextModules: [
      'supportToolkit',
      'subscriptionTimeline',
      'manualRecovery',
      'staffNotes',
    ],
  },
  commerce: {
    slug: 'commerce',
    readinessTone: 'strong',
    availableNow: [
      'plans',
      'subscriptionTemplates',
      'payments',
      'walletOperations',
      'withdrawalApprovals',
    ],
    nextModules: [
      'paymentDetail',
      'manualCorrections',
      'refundResyncFlows',
      'billingOps',
    ],
  },
  growth: {
    slug: 'growth',
    readinessTone: 'partial',
    availableNow: [
      'promoCodes',
      'inviteCodes',
      'partnerPromotion',
      'referralSignals',
    ],
    nextModules: [
      'growthSettings',
      'abuseReview',
      'payoutOps',
      'inviteInventory',
      'fraudSignals',
    ],
  },
  infrastructure: {
    slug: 'infrastructure',
    readinessTone: 'strong',
    availableNow: [
      'servers',
      'hosts',
      'configProfiles',
      'nodePlugins',
      'helix',
      'xray',
    ],
    nextModules: [
      'inbounds',
      'squads',
      'snippets',
      'rolloutConsole',
    ],
  },
  security: {
    slug: 'security',
    readinessTone: 'strong',
    availableNow: [
      'adminSessions',
      'twoFactor',
      'antiPhishing',
      'authHardening',
    ],
    nextModules: [
      'sessionAnomalies',
      'securityPosture',
      'privilegedReasons',
      'deviceTrust',
    ],
  },
  governance: {
    slug: 'governance',
    readinessTone: 'partial',
    availableNow: [
      'auditLog',
      'webhookLog',
      'adminInvites',
      'policyVisibility',
    ],
    nextModules: [
      'adminDirectory',
      'staffRoleChanges',
      'systemConfig',
      'forensicFilters',
    ],
  },
  integrations: {
    slug: 'integrations',
    readinessTone: 'partial',
    availableNow: [
      'telegramOps',
      'botConfigAccess',
      'realtimeTopics',
      'websocketTickets',
    ],
    nextModules: [
      'pushVisibility',
      'deliveryDiagnostics',
      'integrationHealth',
      'opsNotifications',
    ],
  },
};

export function isAdminSectionSlug(
  value: string,
): value is AdminSectionSlug {
  return ADMIN_SECTION_SLUGS.includes(value as AdminSectionSlug);
}
