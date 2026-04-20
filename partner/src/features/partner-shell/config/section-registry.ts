import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Bell,
  Bot,
  Briefcase,
  Building2,
  ChartColumnIncreasing,
  Landmark,
  Megaphone,
  MessageSquare,
  ReceiptText,
  ScrollText,
  Settings,
  Shield,
  Store,
  Ticket,
  Users,
  Waypoints,
} from 'lucide-react';

export const PARTNER_SECTION_SLUGS = [
  'application',
  'organization',
  'team',
  'programs',
  'legal',
  'codes',
  'campaigns',
  'conversions',
  'analytics',
  'finance',
  'compliance',
  'integrations',
  'cases',
  'notifications',
  'settings',
  'reseller',
] as const;

export type PartnerSectionSlug = (typeof PARTNER_SECTION_SLUGS)[number];

export type PartnerNavLabelKey =
  | 'dashboard'
  | 'application'
  | 'organization'
  | 'team'
  | 'programs'
  | 'legal'
  | 'codes'
  | 'campaigns'
  | 'conversions'
  | 'analytics'
  | 'finance'
  | 'compliance'
  | 'integrations'
  | 'cases'
  | 'notifications'
  | 'settings'
  | 'reseller';

export type PartnerNavHintKey =
  | 'dashboardHint'
  | 'applicationHint'
  | 'organizationHint'
  | 'teamHint'
  | 'programsHint'
  | 'legalHint'
  | 'codesHint'
  | 'campaignsHint'
  | 'conversionsHint'
  | 'analyticsHint'
  | 'financeHint'
  | 'complianceHint'
  | 'integrationsHint'
  | 'casesHint'
  | 'notificationsHint'
  | 'settingsHint'
  | 'resellerHint';

export type PartnerPhaseTarget =
  | 'PP0'
  | 'PP1'
  | 'PP2'
  | 'PP3'
  | 'PP4'
  | 'PP5'
  | 'PP6';

export type PartnerReleaseRing = 'R0' | 'R1' | 'R2' | 'R3' | 'R4';

export const PARTNER_RELEASE_RINGS = ['R0', 'R1', 'R2', 'R3', 'R4'] as const satisfies readonly PartnerReleaseRing[];

const PARTNER_RELEASE_RING_ORDER: Record<PartnerReleaseRing, number> = {
  R0: 0,
  R1: 1,
  R2: 2,
  R3: 3,
  R4: 4,
};

export type PartnerAccessStage =
  | 'alwaysVisible'
  | 'applicantVisible'
  | 'probationVisible'
  | 'activeVisible'
  | 'resellerVisible';

export type PartnerAvailableNowKey =
  | 'routeSlot'
  | 'metadata'
  | 'menuPolicy';

export type PartnerNextModuleKey =
  | 'liveData'
  | 'roleActions'
  | 'laneDepth';

export interface PartnerNavItem {
  href: '/dashboard' | `/${PartnerSectionSlug}`;
  icon: LucideIcon;
  labelKey: PartnerNavLabelKey;
  hintKey: PartnerNavHintKey;
}

export interface PartnerSectionOverviewConfig {
  slug: PartnerSectionSlug;
  readinessTone: 'strong' | 'partial' | 'blocked';
  phaseTarget: PartnerPhaseTarget;
  releaseRing: PartnerReleaseRing;
  accessStage: PartnerAccessStage;
  availableNow: readonly PartnerAvailableNowKey[];
  nextModules: readonly PartnerNextModuleKey[];
}

const COMMON_AVAILABLE_NOW = [
  'routeSlot',
  'metadata',
  'menuPolicy',
] as const satisfies readonly PartnerAvailableNowKey[];

const COMMON_NEXT_MODULES = [
  'liveData',
  'roleActions',
  'laneDepth',
] as const satisfies readonly PartnerNextModuleKey[];

export const PARTNER_NAV_ITEMS: readonly PartnerNavItem[] = [
  {
    href: '/dashboard',
    icon: Activity,
    labelKey: 'dashboard',
    hintKey: 'dashboardHint',
  },
  {
    href: '/application',
    icon: Briefcase,
    labelKey: 'application',
    hintKey: 'applicationHint',
  },
  {
    href: '/organization',
    icon: Building2,
    labelKey: 'organization',
    hintKey: 'organizationHint',
  },
  {
    href: '/team',
    icon: Users,
    labelKey: 'team',
    hintKey: 'teamHint',
  },
  {
    href: '/programs',
    icon: Waypoints,
    labelKey: 'programs',
    hintKey: 'programsHint',
  },
  {
    href: '/legal',
    icon: ScrollText,
    labelKey: 'legal',
    hintKey: 'legalHint',
  },
  {
    href: '/codes',
    icon: Ticket,
    labelKey: 'codes',
    hintKey: 'codesHint',
  },
  {
    href: '/campaigns',
    icon: Megaphone,
    labelKey: 'campaigns',
    hintKey: 'campaignsHint',
  },
  {
    href: '/conversions',
    icon: ReceiptText,
    labelKey: 'conversions',
    hintKey: 'conversionsHint',
  },
  {
    href: '/analytics',
    icon: ChartColumnIncreasing,
    labelKey: 'analytics',
    hintKey: 'analyticsHint',
  },
  {
    href: '/finance',
    icon: Landmark,
    labelKey: 'finance',
    hintKey: 'financeHint',
  },
  {
    href: '/compliance',
    icon: Shield,
    labelKey: 'compliance',
    hintKey: 'complianceHint',
  },
  {
    href: '/integrations',
    icon: Bot,
    labelKey: 'integrations',
    hintKey: 'integrationsHint',
  },
  {
    href: '/cases',
    icon: MessageSquare,
    labelKey: 'cases',
    hintKey: 'casesHint',
  },
  {
    href: '/notifications',
    icon: Bell,
    labelKey: 'notifications',
    hintKey: 'notificationsHint',
  },
  {
    href: '/settings',
    icon: Settings,
    labelKey: 'settings',
    hintKey: 'settingsHint',
  },
  {
    href: '/reseller',
    icon: Store,
    labelKey: 'reseller',
    hintKey: 'resellerHint',
  },
] as const;

export const PARTNER_SECTION_OVERVIEWS: Record<
  PartnerSectionSlug,
  PartnerSectionOverviewConfig
> = {
  application: {
    slug: 'application',
    readinessTone: 'strong',
    phaseTarget: 'PP1',
    releaseRing: 'R1',
    accessStage: 'applicantVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  organization: {
    slug: 'organization',
    readinessTone: 'strong',
    phaseTarget: 'PP1',
    releaseRing: 'R1',
    accessStage: 'alwaysVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  team: {
    slug: 'team',
    readinessTone: 'partial',
    phaseTarget: 'PP3',
    releaseRing: 'R2',
    accessStage: 'probationVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  programs: {
    slug: 'programs',
    readinessTone: 'partial',
    phaseTarget: 'PP3',
    releaseRing: 'R1',
    accessStage: 'applicantVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  legal: {
    slug: 'legal',
    readinessTone: 'partial',
    phaseTarget: 'PP3',
    releaseRing: 'R1',
    accessStage: 'alwaysVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  codes: {
    slug: 'codes',
    readinessTone: 'partial',
    phaseTarget: 'PP4',
    releaseRing: 'R1',
    accessStage: 'probationVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  campaigns: {
    slug: 'campaigns',
    readinessTone: 'partial',
    phaseTarget: 'PP4',
    releaseRing: 'R1',
    accessStage: 'probationVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  conversions: {
    slug: 'conversions',
    readinessTone: 'blocked',
    phaseTarget: 'PP6',
    releaseRing: 'R2',
    accessStage: 'activeVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  analytics: {
    slug: 'analytics',
    readinessTone: 'partial',
    phaseTarget: 'PP5',
    releaseRing: 'R1',
    accessStage: 'probationVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  finance: {
    slug: 'finance',
    readinessTone: 'partial',
    phaseTarget: 'PP5',
    releaseRing: 'R1',
    accessStage: 'probationVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  compliance: {
    slug: 'compliance',
    readinessTone: 'partial',
    phaseTarget: 'PP4',
    releaseRing: 'R1',
    accessStage: 'probationVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  integrations: {
    slug: 'integrations',
    readinessTone: 'blocked',
    phaseTarget: 'PP6',
    releaseRing: 'R3',
    accessStage: 'activeVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  cases: {
    slug: 'cases',
    readinessTone: 'strong',
    phaseTarget: 'PP2',
    releaseRing: 'R1',
    accessStage: 'applicantVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  notifications: {
    slug: 'notifications',
    readinessTone: 'strong',
    phaseTarget: 'PP2',
    releaseRing: 'R0',
    accessStage: 'alwaysVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  settings: {
    slug: 'settings',
    readinessTone: 'strong',
    phaseTarget: 'PP1',
    releaseRing: 'R1',
    accessStage: 'alwaysVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
  reseller: {
    slug: 'reseller',
    readinessTone: 'blocked',
    phaseTarget: 'PP6',
    releaseRing: 'R4',
    accessStage: 'resellerVisible',
    availableNow: COMMON_AVAILABLE_NOW,
    nextModules: COMMON_NEXT_MODULES,
  },
};

export function isPartnerSectionSlug(
  value: string,
): value is PartnerSectionSlug {
  return PARTNER_SECTION_SLUGS.includes(value as PartnerSectionSlug);
}

export function isPartnerReleaseRing(
  value: string,
): value is PartnerReleaseRing {
  return PARTNER_RELEASE_RINGS.includes(value as PartnerReleaseRing);
}

export function doesPartnerReleaseRingMeetRequirement(
  currentRing: PartnerReleaseRing,
  requiredRing: PartnerReleaseRing,
): boolean {
  return PARTNER_RELEASE_RING_ORDER[currentRing] >= PARTNER_RELEASE_RING_ORDER[requiredRing];
}

export function getPartnerRouteRequiredReleaseRing(
  route: 'dashboard' | PartnerSectionSlug,
): PartnerReleaseRing {
  return route === 'dashboard' ? 'R0' : PARTNER_SECTION_OVERVIEWS[route].releaseRing;
}
