'use client';

import { AlertTriangle, Bell, Briefcase, MessageSquare, ShieldCheck } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import {
  PARTNER_NAV_ITEMS,
  PARTNER_SECTION_SLUGS,
  PARTNER_RELEASE_RINGS,
  getPartnerRouteRequiredReleaseRing,
  type PartnerSectionSlug,
  type PartnerReleaseRing,
  type PartnerNavItem,
} from '@/features/partner-shell/config/section-registry';
import {
  applyPartnerWorkspaceRole,
  applyPartnerReleaseRing,
  applyPartnerPortalScenario,
  type PartnerWorkspaceRole,
  type PartnerPortalScenario,
  type PartnerReviewRequestKind,
} from '@/features/partner-portal-state/lib/portal-state';
import {
  canPartnerRouteAccess,
  countPartnerAccessibleSections,
  getPartnerRoleRouteAccess,
} from '@/features/partner-portal-state/lib/portal-access';
import {
  getPartnerRouteBlockReason,
  getPartnerRouteVisibility,
  getPartnerVisibilityBand,
  type PartnerRouteKey,
  type PartnerSectionVisibility,
} from '@/features/partner-portal-state/lib/portal-visibility';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

type DashboardRouteHref = '/dashboard' | `/${PartnerSectionSlug}`;

type DashboardTone = 'good' | 'warning' | 'critical' | 'neutral';

type DashboardTaskCard = {
  id: string;
  title: string;
  description: string;
  tone: Exclude<DashboardTone, 'good'>;
  href: DashboardRouteHref;
};

type DashboardSectionGroupId =
  | 'main'
  | 'onboarding'
  | 'workspace'
  | 'promotion'
  | 'results'
  | 'finance'
  | 'control'
  | 'technical';

type DashboardSectionGroupConfig = {
  id: DashboardSectionGroupId;
  titleKey: string;
  descriptionKey: string;
  routes: readonly PartnerSectionSlug[];
};

type DashboardSectionEntry = {
  item: PartnerNavItem;
  routeKey: PartnerSectionSlug;
  visibility: PartnerSectionVisibility;
  access: ReturnType<typeof getPartnerRoleRouteAccess>;
};

type DashboardConstraint = {
  id: string;
  title: string;
  description: string;
  tone: DashboardTone;
  href: DashboardRouteHref;
};

const SCENARIO_OPTIONS: PartnerPortalScenario[] = [
  'draft',
  'needs_info',
  'under_review',
  'waitlisted',
  'approved_probation',
  'active',
  'restricted',
];

const WORKSPACE_ROLE_OPTIONS: PartnerWorkspaceRole[] = [
  'workspace_owner',
  'finance_manager',
  'analyst',
  'traffic_manager',
  'support_manager',
  'workspace_admin',
  'technical_manager',
  'legal_compliance_manager',
];

const REVIEW_REQUEST_ROUTE_MAP = {
  business_profile: '/organization',
  owned_channels: '/application',
  traffic_methods: '/application',
  support_ownership: '/cases',
  finance_profile: '/finance',
} as const satisfies Record<PartnerReviewRequestKind, DashboardRouteHref>;

const READINESS_ROUTE_MAP: Record<string, DashboardRouteHref> = {
  finance: '/finance',
  compliance: '/compliance',
  technical: '/integrations',
  governance: '/compliance',
};

const TASK_ACTION_LABEL_KEYS = {
  '/dashboard': 'taskActions.dashboard',
  '/application': 'taskActions.application',
  '/organization': 'taskActions.organization',
  '/team': 'taskActions.team',
  '/programs': 'taskActions.programs',
  '/legal': 'taskActions.legal',
  '/codes': 'taskActions.codes',
  '/campaigns': 'taskActions.campaigns',
  '/conversions': 'taskActions.conversions',
  '/analytics': 'taskActions.analytics',
  '/finance': 'taskActions.finance',
  '/compliance': 'taskActions.compliance',
  '/integrations': 'taskActions.integrations',
  '/cases': 'taskActions.cases',
  '/notifications': 'taskActions.notifications',
  '/settings': 'taskActions.settings',
  '/reseller': 'taskActions.reseller',
} as const satisfies Record<DashboardRouteHref, string>;

const DASHBOARD_SECTION_GROUPS: readonly DashboardSectionGroupConfig[] = [
  {
    id: 'main',
    titleKey: 'sections.groups.main.title',
    descriptionKey: 'sections.groups.main.description',
    routes: ['notifications'],
  },
  {
    id: 'onboarding',
    titleKey: 'sections.groups.onboarding.title',
    descriptionKey: 'sections.groups.onboarding.description',
    routes: ['application', 'organization', 'legal'],
  },
  {
    id: 'workspace',
    titleKey: 'sections.groups.workspace.title',
    descriptionKey: 'sections.groups.workspace.description',
    routes: ['team', 'settings'],
  },
  {
    id: 'promotion',
    titleKey: 'sections.groups.promotion.title',
    descriptionKey: 'sections.groups.promotion.description',
    routes: ['programs', 'codes', 'campaigns'],
  },
  {
    id: 'results',
    titleKey: 'sections.groups.results.title',
    descriptionKey: 'sections.groups.results.description',
    routes: ['conversions', 'analytics'],
  },
  {
    id: 'finance',
    titleKey: 'sections.groups.finance.title',
    descriptionKey: 'sections.groups.finance.description',
    routes: ['finance'],
  },
  {
    id: 'control',
    titleKey: 'sections.groups.control.title',
    descriptionKey: 'sections.groups.control.description',
    routes: ['compliance', 'cases'],
  },
  {
    id: 'technical',
    titleKey: 'sections.groups.technical.title',
    descriptionKey: 'sections.groups.technical.description',
    routes: ['integrations', 'reseller'],
  },
];

const DASHBOARD_FOCUS_RING_CLASS = 'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]';
const DASHBOARD_ACTION_LINK_BASE_CLASS = 'inline-flex min-h-11 items-center justify-center rounded-full border border-grid-line/25 bg-terminal-bg/60 px-4 py-2 text-center font-mono transition-colors';
const DASHBOARD_ACTION_LINK_CLASS = `${DASHBOARD_ACTION_LINK_BASE_CLASS} text-sm text-neon-cyan hover:border-neon-cyan/40 ${DASHBOARD_FOCUS_RING_CLASS}`;
const DASHBOARD_TASK_ACTION_LINK_CLASS = `${DASHBOARD_ACTION_LINK_BASE_CLASS} text-xs uppercase tracking-[0.16em] text-neon-cyan hover:border-neon-cyan/40 ${DASHBOARD_FOCUS_RING_CLASS}`;
const DASHBOARD_SECTION_CARD_LINK_CLASS = `rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4 transition-colors hover:border-neon-cyan/35 ${DASHBOARD_FOCUS_RING_CLASS}`;

function isPartnerRouteKey(value: string | null | undefined): value is PartnerRouteKey {
  return value === 'dashboard' || PARTNER_SECTION_SLUGS.includes(value as PartnerSectionSlug);
}

function hrefFromRouteKey(route: PartnerRouteKey): DashboardRouteHref {
  return route === 'dashboard' ? '/dashboard' : `/${route}`;
}

function hrefFromRouteSlug(routeSlug: string | null | undefined): DashboardRouteHref | null {
  return isPartnerRouteKey(routeSlug) ? hrefFromRouteKey(routeSlug) : null;
}

function routeKeyFromHref(href: DashboardRouteHref): PartnerRouteKey {
  return href === '/dashboard' ? 'dashboard' : href.slice(1) as PartnerSectionSlug;
}

function resolveAccessibleHref(
  href: DashboardRouteHref,
  state: Parameters<typeof canPartnerRouteAccess>[1],
): DashboardRouteHref {
  const routeKey = routeKeyFromHref(href);

  if (routeKey === 'dashboard' || canPartnerRouteAccess(routeKey, state)) {
    return href;
  }

  return canPartnerRouteAccess('cases', state) ? '/cases' : '/dashboard';
}

function getReadinessTaskHref(sourceId: string | null | undefined): DashboardRouteHref {
  return sourceId && sourceId in READINESS_ROUTE_MAP
    ? READINESS_ROUTE_MAP[sourceId]
    : '/cases';
}

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function toneClass(value: DashboardTone) {
  if (value === 'good') {
    return 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green';
  }

  if (value === 'warning') {
    return 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan';
  }

  if (value === 'critical') {
    return 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink';
  }

  return 'border-grid-line/25 bg-terminal-surface/40 text-muted-foreground';
}

function formatBootstrapPendingTask(
  task: {
    task_key: string;
    tone: string;
    route_slug?: string | null;
    source_kind?: string | null;
    source_id?: string | null;
    notes?: readonly string[];
  },
  partnerT: (key: string, values?: Record<string, string | number>) => string,
): DashboardTaskCard {
  const explicitHref = hrefFromRouteSlug(task.route_slug);

  if (task.source_kind === 'review_request' && task.task_key.startsWith('review_request.')) {
    const kind = task.task_key.slice('review_request.'.length);
    const href = kind in REVIEW_REQUEST_ROUTE_MAP
      ? REVIEW_REQUEST_ROUTE_MAP[kind as PartnerReviewRequestKind]
      : '/cases';

    return {
      id: task.task_key,
      title: partnerT(`portalState.reviewRequestKinds.${kind}.title`),
      description: partnerT(`portalState.reviewRequestKinds.${kind}.description`),
      tone: task.tone === 'critical' ? 'critical' as const : 'warning' as const,
      href: explicitHref ?? href,
    };
  }

  if (task.source_kind === 'readiness' && task.source_id) {
    const stateKey = task.task_key.split('.').at(-1) ?? 'not_started';
    const stateNamespace = task.source_id === 'finance'
      ? 'financeStates'
      : task.source_id === 'compliance'
        ? 'complianceStates'
        : 'technicalStates';

    return {
      id: task.task_key,
      title: partnerT(`portalState.readinessLabels.${task.source_id}`),
      description: partnerT(`portalState.${stateNamespace}.${stateKey}`),
      tone: task.tone === 'critical' ? 'critical' as const : 'warning' as const,
      href: explicitHref ?? getReadinessTaskHref(task.source_id),
    };
  }

  return {
    id: task.task_key,
    title: task.task_key,
    description: task.notes?.[0] ?? '',
    tone: task.tone === 'critical' ? 'critical' as const : 'neutral' as const,
    href: explicitHref ?? '/cases',
  };
}

export function PartnerDashboardPage() {
  const locale = useLocale();
  const t = useTranslations('Dashboard');
  const navT = useTranslations('Navigation');
  const partnerT = useTranslations('Partner');
  const {
    state,
    isCanonicalWorkspace,
    isSimulationEnabled,
    counters,
    pendingTasks: bootstrapPendingTasks,
    blockedReasons,
  } = usePartnerPortalRuntimeState();
  const showSimulationControls = isSimulationEnabled && !isCanonicalWorkspace;

  const visibilityBand = getPartnerVisibilityBand(state.workspaceStatus);
  const pendingReviewRequests = state.reviewRequests.filter((request) => request.status === 'open');
  const unreadNotifications = state.notifications.filter((notification) => notification.unread);
  const openCases = state.cases.filter((item) => item.status !== 'resolved');
  const accessibleSectionCount = countPartnerAccessibleSections(state);
  const spotlightMetrics = state.analyticsMetrics.slice(0, 3);
  const visibleSectionEntries = PARTNER_NAV_ITEMS
    .filter((item) => item.href !== '/dashboard')
    .map((item): DashboardSectionEntry | null => {
      const routeKey = item.href.slice(1) as PartnerSectionSlug;
      if (!canPartnerRouteAccess(routeKey, state)) {
        return null;
      }

      return {
        item,
        routeKey,
        visibility: getPartnerRouteVisibility(routeKey, state),
        access: getPartnerRoleRouteAccess(routeKey, state),
      };
    })
    .filter((item): item is DashboardSectionEntry => item !== null);
  const visibleSectionGroups = DASHBOARD_SECTION_GROUPS
    .map((group) => ({
      ...group,
      items: group.routes
        .map((routeKey) => visibleSectionEntries.find((entry) => entry.routeKey === routeKey) ?? null)
        .filter((item): item is DashboardSectionEntry => item !== null),
    }))
    .filter((group) => group.items.length > 0);
  const releaseRingBlockedSections = PARTNER_NAV_ITEMS.filter((item) => (
    item.href !== '/dashboard'
    && getPartnerRouteBlockReason(item.href.slice(1) as PartnerSectionSlug, state) === 'release_ring'
  ));
  const taskSections = visibleSectionEntries.filter((entry) => entry.visibility === 'task');
  const limitedSections = visibleSectionEntries.filter((entry) => entry.visibility === 'limited');
  const readOnlySections = visibleSectionEntries.filter((entry) => entry.visibility === 'read');

  const localPendingTasks: DashboardTaskCard[] = [
    ...pendingReviewRequests.map((request) => ({
      id: request.id,
      title: partnerT(`portalState.reviewRequestKinds.${request.kind}.title`),
      description: partnerT(`portalState.reviewRequestKinds.${request.kind}.description`),
      tone: 'warning' as const,
      href: REVIEW_REQUEST_ROUTE_MAP[request.kind],
    })),
    ...(state.financeReadiness === 'blocked'
      ? [{
          id: 'finance-blocked',
          title: partnerT('portalState.blockedOutcomes.finance.title'),
          description: partnerT('portalState.blockedOutcomes.finance.description'),
          tone: 'critical' as const,
          href: '/finance' as const,
        }]
      : []),
    ...(state.complianceReadiness === 'evidence_requested'
      ? [{
          id: 'compliance-evidence',
          title: partnerT('portalState.blockedOutcomes.compliance.title'),
          description: partnerT('portalState.blockedOutcomes.compliance.description'),
          tone: 'warning' as const,
          href: '/compliance' as const,
        }]
      : []),
  ];
  const pendingTasks = (bootstrapPendingTasks.length > 0
    ? bootstrapPendingTasks.map((task) => ({
        ...formatBootstrapPendingTask(task, partnerT),
        id: task.id,
      }))
    : localPendingTasks).map((task) => {
      const href = resolveAccessibleHref(task.href, state);

      return {
        ...task,
        href,
        actionLabel: t(TASK_ACTION_LABEL_KEYS[href]),
      };
    });
  const pendingTaskCount = isCanonicalWorkspace
    ? (counters?.pending_tasks ?? pendingTasks.length)
    : pendingTasks.length;
  const unreadNotificationCount = isCanonicalWorkspace
    ? (counters?.unread_notifications ?? unreadNotifications.length)
    : unreadNotifications.length;
  const openCaseCount = isCanonicalWorkspace
    ? (counters?.open_cases ?? openCases.length)
    : openCases.length;
  const commandConstraints: DashboardConstraint[] = [
    ...blockedReasons.map((reason) => ({
      id: `canonical:${reason.code}`,
      title: t('constraints.canonicalReasonTitle', { code: reason.code }),
      description: reason.notes?.[0] ?? t('constraints.canonicalReasonDescription'),
      tone: reason.severity === 'critical'
        ? 'critical' as const
        : reason.severity === 'warning'
          ? 'warning' as const
          : 'neutral' as const,
      href: resolveAccessibleHref(hrefFromRouteSlug(reason.route_slug) ?? '/cases', state),
    })),
    ...(releaseRingBlockedSections.length > 0
      ? [{
          id: 'release-ring',
          title: t('constraints.releaseRingTitle'),
          description: t('constraints.releaseRingDescription', {
            count: releaseRingBlockedSections.length,
          }),
          tone: 'warning' as const,
          href: '/notifications' as const,
        }]
      : []),
    ...(taskSections.length > 0
      ? [{
          id: 'task-sections',
          title: t('constraints.taskTitle'),
          description: t('constraints.taskDescription', {
            count: taskSections.length,
          }),
          tone: 'warning' as const,
          href: taskSections[0]?.item.href ?? '/dashboard',
        }]
      : []),
    ...(limitedSections.length > 0
      ? [{
          id: 'limited-sections',
          title: t('constraints.limitedTitle'),
          description: t('constraints.limitedDescription', {
            count: limitedSections.length,
          }),
          tone: 'neutral' as const,
          href: limitedSections[0]?.item.href ?? '/dashboard',
        }]
      : []),
    ...(readOnlySections.length > 0
      ? [{
          id: 'read-only-sections',
          title: t('constraints.readOnlyTitle'),
          description: t('constraints.readOnlyDescription', {
            count: readOnlySections.length,
          }),
          tone: 'neutral' as const,
          href: readOnlySections[0]?.item.href ?? '/dashboard',
        }]
      : []),
  ];

  return (
    <section className="space-y-6">
      <header className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className={cn('inline-flex rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em]', toneClass(
                state.workspaceStatus === 'active'
                  ? 'good'
                  : state.workspaceStatus === 'restricted' || state.workspaceStatus === 'waitlisted'
                    ? 'critical'
                    : 'warning',
              ))}>
                {partnerT(`portalState.workspaceStatuses.${state.workspaceStatus}`)}
              </span>
              <span className="inline-flex rounded-full border border-grid-line/25 bg-terminal-surface/40 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                {partnerT(`portalState.visibilityBands.${visibilityBand}`)}
              </span>
              <span className="inline-flex rounded-full border border-grid-line/25 bg-terminal-surface/40 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                {state.primaryLane
                  ? partnerT(`portalState.laneLabels.${state.primaryLane}`)
                  : partnerT('portalState.noLane')}
              </span>
              <span className="inline-flex rounded-full border border-grid-line/25 bg-terminal-surface/40 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                {partnerT(`portalState.workspaceRoles.${state.workspaceRole}`)}
              </span>
              <span className="inline-flex rounded-full border border-grid-line/25 bg-terminal-surface/40 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                {partnerT(`portalState.releaseRings.${state.releaseRing}`)}
              </span>
            </div>

            <div>
              <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('eyebrow')}
              </p>
              <h1 className="mt-2 text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
                {t('title')}
              </h1>
              <p className="mt-3 max-w-4xl text-sm font-mono leading-6 text-muted-foreground">
                {t('subtitle')}
              </p>
            </div>

            <dl className="grid gap-3 text-sm font-mono text-muted-foreground md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.workspaceStatusLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {partnerT(`portalState.workspaceStatuses.${state.workspaceStatus}`)}
                </dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.currentLaneLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {state.primaryLane
                    ? partnerT(`portalState.laneLabels.${state.primaryLane}`)
                    : partnerT('portalState.noLane')}
                </dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.visibilityBandLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {partnerT(`portalState.visibilityBands.${visibilityBand}`)}
                </dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.updatedAtLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {state.updatedAt
                    ? formatDateTime(state.updatedAt, locale)
                    : partnerT('portalState.notSaved')}
                </dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.workspaceRoleLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {partnerT(`portalState.workspaceRoles.${state.workspaceRole}`)}
                </dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.releaseRingLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {partnerT(`portalState.releaseRings.${state.releaseRing}`)}
                </dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
                  {partnerT('portalState.accessibleSectionsLabel')}
                </dt>
                <dd className="mt-2 text-foreground">
                  {accessibleSectionCount}
                </dd>
              </div>
            </dl>
          </div>

          {showSimulationControls ? (
            <div className="space-y-4 rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 xl:w-[340px]">
            <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
              {t('scenario.label')}
            </p>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('scenario.description')}
            </p>
            <select
              value={state.scenario}
              onChange={(event) => applyPartnerPortalScenario(event.target.value as PartnerPortalScenario)}
              disabled={isCanonicalWorkspace}
              className="mt-4 w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20"
            >
              {SCENARIO_OPTIONS.map((scenario) => (
                <option key={scenario} value={scenario}>
                  {t(`scenario.options.${scenario}`)}
                </option>
              ))}
            </select>
            <p className="mt-3 text-xs font-mono leading-5 text-muted-foreground">
              {isCanonicalWorkspace
                ? t('scenario.canonicalDisabled')
                : t('scenario.helper')}
            </p>

            <div className="border-t border-grid-line/20 pt-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('role.label')}
              </p>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('role.description')}
              </p>
              <select
                value={state.workspaceRole}
                onChange={(event) => applyPartnerWorkspaceRole(event.target.value as PartnerWorkspaceRole)}
                disabled={isCanonicalWorkspace}
                className="mt-4 w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20"
              >
                {WORKSPACE_ROLE_OPTIONS.map((role) => (
                  <option key={role} value={role}>
                    {partnerT(`portalState.workspaceRoles.${role}`)}
                  </option>
                ))}
              </select>
              <p className="mt-3 text-xs font-mono leading-5 text-muted-foreground">
                {isCanonicalWorkspace
                  ? t('role.canonicalDisabled')
                  : t('role.helper')}
              </p>
            </div>

            <div className="border-t border-grid-line/20 pt-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('releaseRing.label')}
              </p>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('releaseRing.description')}
              </p>
              <select
                value={state.releaseRing}
                onChange={(event) => applyPartnerReleaseRing(event.target.value as PartnerReleaseRing)}
                className="mt-4 w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20"
              >
                {PARTNER_RELEASE_RINGS.map((releaseRing) => (
                  <option key={releaseRing} value={releaseRing}>
                    {partnerT(`portalState.releaseRings.${releaseRing}`)}
                  </option>
                ))}
              </select>
              <p className="mt-3 text-xs font-mono leading-5 text-muted-foreground">
                {t('releaseRing.helper')}
              </p>
            </div>
          </div>
          ) : null}
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <div className="flex items-center justify-between gap-3">
            <ShieldCheck className="h-5 w-5 text-neon-cyan" />
            <span className={cn('inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]', toneClass('warning'))}>
              {partnerT(`portalState.workspaceStatuses.${state.workspaceStatus}`)}
            </span>
          </div>
          <p className="mt-4 text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('cards.workspaceStatus.title')}
          </p>
          <p className="mt-2 text-2xl font-display tracking-[0.14em] text-white">
            {partnerT(`portalState.visibilityBands.${visibilityBand}`)}
          </p>
          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
            {t('cards.workspaceStatus.description')}
          </p>
        </article>

        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <div className="flex items-center justify-between gap-3">
            <AlertTriangle className="h-5 w-5 text-neon-pink" />
            <span className={cn('inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]', toneClass(pendingTaskCount > 0 ? 'critical' : 'good'))}>
              {pendingTaskCount}
            </span>
          </div>
          <p className="mt-4 text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('cards.pendingTasks.title')}
          </p>
          <p className="mt-2 text-2xl font-display tracking-[0.14em] text-white">
            {pendingTaskCount}
          </p>
          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
            {t('cards.pendingTasks.description')}
          </p>
        </article>

        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <div className="flex items-center justify-between gap-3">
            <Bell className="h-5 w-5 text-neon-cyan" />
            <span className={cn('inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]', toneClass(unreadNotificationCount > 0 ? 'warning' : 'good'))}>
              {unreadNotificationCount}
            </span>
          </div>
          <p className="mt-4 text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('cards.notifications.title')}
          </p>
          <p className="mt-2 text-2xl font-display tracking-[0.14em] text-white">
            {state.notifications.length}
          </p>
          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
            {t('cards.notifications.description')}
          </p>
        </article>

        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <div className="flex items-center justify-between gap-3">
            <MessageSquare className="h-5 w-5 text-neon-purple" />
            <span className={cn('inline-flex rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.18em]', toneClass(openCaseCount > 0 ? 'warning' : 'good'))}>
              {openCaseCount}
            </span>
          </div>
          <p className="mt-4 text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('cards.cases.title')}
          </p>
          <p className="mt-2 text-2xl font-display tracking-[0.14em] text-white">
            {openCaseCount}
          </p>
          <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
            {t('cards.cases.description')}
          </p>
        </article>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
          <div className="flex items-center justify-between gap-3 border-b border-grid-line/20 pb-4">
            <div>
              <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                {t('tasks.title')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('tasks.description')}
              </p>
            </div>
            <Link
              href="/cases"
              className={DASHBOARD_ACTION_LINK_CLASS}
            >
              {t('tasks.openCases')}
            </Link>
          </div>

          {pendingTasks.length === 0 ? (
            <p className="mt-5 text-sm font-mono leading-6 text-muted-foreground">
              {partnerT('portalState.tasks.empty')}
            </p>
          ) : (
            <div className="mt-5 space-y-3">
              {pendingTasks.map((task) => (
                <article
                  key={task.id}
                  className={cn('rounded-2xl border p-4', toneClass(task.tone))}
                >
                  <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {task.title}
                  </h3>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {task.description}
                  </p>
                  <Link
                    href={task.href}
                    className={cn('mt-4', DASHBOARD_TASK_ACTION_LINK_CLASS)}
                  >
                    {task.actionLabel}
                  </Link>
                </article>
              ))}
            </div>
          )}
        </article>

        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
          <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
            {t('readiness.title')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('readiness.description')}
          </p>

          <dl className="mt-5 space-y-3">
            {[
              ['finance', state.financeReadiness],
              ['compliance', state.complianceReadiness],
              ['technical', state.technicalReadiness],
              ['governance', state.governanceState],
            ].map(([key, value]) => (
              <div
                key={key}
                className="flex items-center justify-between gap-3 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 px-4 py-3 text-sm font-mono"
              >
                <dt className="text-muted-foreground">
                  {partnerT(`portalState.readinessLabels.${key}`)}
                </dt>
                <dd className="text-foreground">
                  {partnerT(`portalState.${key}States.${value}`)}
                </dd>
              </div>
            ))}
          </dl>

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
              {t('constraints.title')}
            </h3>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('constraints.description')}
            </p>

            {commandConstraints.length === 0 ? (
              <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                {t('constraints.empty')}
              </p>
            ) : (
              <div className="mt-4 space-y-3">
                {commandConstraints.map((constraint) => (
                  <article
                    key={constraint.id}
                    className={cn('rounded-2xl border p-4', toneClass(constraint.tone))}
                  >
                    <h4 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {constraint.title}
                    </h4>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {constraint.description}
                    </p>
                    <Link
                      href={constraint.href}
                      className={cn('mt-4', DASHBOARD_TASK_ACTION_LINK_CLASS)}
                    >
                      {t(TASK_ACTION_LABEL_KEYS[constraint.href])}
                    </Link>
                  </article>
                ))}
              </div>
            )}
          </div>
        </article>
      </div>

      {(spotlightMetrics.length > 0 || state.financeStatements.length > 0) ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
            <div className="flex items-center justify-between gap-3 border-b border-grid-line/20 pb-4">
              <div>
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('performanceSnapshot.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('performanceSnapshot.description')}
                </p>
              </div>
              <Link href="/analytics" className={DASHBOARD_ACTION_LINK_CLASS}>
                {t('performanceSnapshot.open')}
              </Link>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {spotlightMetrics.map((metric) => (
                <article
                  key={metric.key}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                >
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                    {partnerT(`portalState.analyticsMetricKeys.${metric.key}`)}
                  </p>
                  <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                    {metric.value}
                  </p>
                  <p className="mt-2 text-xs font-mono text-muted-foreground">
                    {partnerT(`portalState.analyticsMetricTrends.${metric.trend}`)}
                  </p>
                </article>
              ))}
            </div>
          </article>

          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
            <div className="flex items-center justify-between gap-3 border-b border-grid-line/20 pb-4">
              <div>
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('financeSnapshot.title')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('financeSnapshot.description')}
                </p>
              </div>
              <Link href="/finance" className={DASHBOARD_ACTION_LINK_CLASS}>
                {t('financeSnapshot.open')}
              </Link>
            </div>
            <dl className="mt-5 grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">{t('financeSnapshot.available')}</dt>
                <dd className="mt-2 text-xl font-display tracking-[0.12em] text-white">{state.financeSnapshot.availableEarnings}</dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">{t('financeSnapshot.onHold')}</dt>
                <dd className="mt-2 text-xl font-display tracking-[0.12em] text-white">{state.financeSnapshot.onHoldEarnings}</dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">{t('financeSnapshot.reserves')}</dt>
                <dd className="mt-2 text-xl font-display tracking-[0.12em] text-white">{state.financeSnapshot.reserves}</dd>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
                <dt className="text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">{t('financeSnapshot.forecast')}</dt>
                <dd className="mt-2 text-xl font-display tracking-[0.12em] text-white">{state.financeSnapshot.nextPayoutForecast}</dd>
              </div>
            </dl>
          </article>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
          <div className="border-b border-grid-line/20 pb-4">
            <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
              {t('sections.title')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('sections.description')}
            </p>
          </div>

          <div className="mt-5 space-y-4">
            {visibleSectionGroups.map((group) => (
              <section
                key={group.id}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
              >
                <div className="flex flex-col gap-2 border-b border-grid-line/20 pb-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {t(group.titleKey)}
                    </h3>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t(group.descriptionKey)}
                    </p>
                  </div>
                  <span className="inline-flex w-fit rounded-full border border-grid-line/25 bg-terminal-surface/35 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {group.items.length}
                  </span>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {group.items.map(({ item, visibility, access }) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={DASHBOARD_SECTION_CARD_LINK_CLASS}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {navT(item.labelKey)}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {navT(item.hintKey)}
                          </p>
                        </div>
                        <span className={cn('rounded-full border px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.16em]', toneClass(
                          visibility === 'full'
                            ? 'good'
                            : visibility === 'task' || visibility === 'limited'
                              ? 'warning'
                              : 'neutral',
                        ))}>
                          {partnerT(`portalState.routeVisibility.${visibility}`)}
                        </span>
                      </div>
                      <p className="mt-4 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                        {partnerT('portalState.currentAccessLabel')}: {partnerT(`portalState.routeAccess.${access}`)}
                      </p>
                      {visibility !== 'full' ? (
                        <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                          {t(`sections.stateDescriptions.${visibility}`)}
                        </p>
                      ) : null}
                    </Link>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-6 rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {t('rollout.title')}
                </h3>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('rollout.description')}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                <span className="rounded-full border border-grid-line/25 bg-terminal-surface/35 px-3 py-1">
                  {t('rollout.currentRing')}: {partnerT(`portalState.releaseRings.${state.releaseRing}`)}
                </span>
                <span className="rounded-full border border-grid-line/25 bg-terminal-surface/35 px-3 py-1">
                  {t('rollout.blockedCount')}: {releaseRingBlockedSections.length}
                </span>
              </div>
            </div>

            {releaseRingBlockedSections.length === 0 ? (
              <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                {t('rollout.empty')}
              </p>
            ) : (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {releaseRingBlockedSections.map((item) => {
                  const routeKey = item.href.slice(1) as PartnerSectionSlug;
                  const requiredReleaseRing = getPartnerRouteRequiredReleaseRing(routeKey);

                  return (
                    <article
                      key={item.href}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                    >
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {navT(item.labelKey)}
                      </p>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {navT(item.hintKey)}
                      </p>
                      <p className="mt-4 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink">
                        {t('rollout.opensAt', {
                          ring: partnerT(`portalState.releaseRings.${requiredReleaseRing}`),
                        })}
                      </p>
                      <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {partnerT('portalState.currentAccessLabel')}: {partnerT('portalState.routeAccess.none')}
                      </p>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </article>

        <div className="space-y-6">
          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                {t('notificationsPanel.title')}
              </h2>
              <Link href="/notifications" className={DASHBOARD_ACTION_LINK_CLASS}>
                {t('notificationsPanel.open')}
              </Link>
            </div>
            <div className="mt-4 space-y-3">
              {state.notifications.slice(0, 3).map((notification) => (
                <article
                  key={notification.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                >
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {partnerT(`portalState.notificationKinds.${notification.kind}.title`)}
                  </p>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {notification.message || partnerT(`portalState.notificationKinds.${notification.kind}.description`)}
                  </p>
                </article>
              ))}
            </div>
          </article>

          <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                {t('casesPanel.title')}
              </h2>
              <Link href="/cases" className={DASHBOARD_ACTION_LINK_CLASS}>
                {t('casesPanel.open')}
              </Link>
            </div>
            <div className="mt-4 space-y-3">
              {state.cases.slice(0, 3).map((item) => (
                <article
                  key={item.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                >
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {partnerT(`portalState.caseKinds.${item.kind}.title`)}
                  </p>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {partnerT(`portalState.caseStatuses.${item.status}`)}
                  </p>
                </article>
              ))}
            </div>
          </article>
        </div>
      </div>

      <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
        <div className="flex flex-wrap items-center gap-3">
          <Briefcase className="h-5 w-5 text-neon-cyan" />
          <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
            {t('nextActions.title')}
          </h2>
        </div>
        <p className="mt-3 max-w-4xl text-sm font-mono leading-6 text-muted-foreground">
          {t('nextActions.description')}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/application"
            className={cn(DASHBOARD_ACTION_LINK_BASE_CLASS, 'text-sm text-neon-cyan hover:border-neon-cyan/40', DASHBOARD_FOCUS_RING_CLASS)}
          >
            {t('nextActions.application')}
          </Link>
          <Link
            href="/cases"
            className={cn(DASHBOARD_ACTION_LINK_BASE_CLASS, 'text-sm text-neon-purple hover:border-neon-purple/40', DASHBOARD_FOCUS_RING_CLASS)}
          >
            {t('nextActions.cases')}
          </Link>
          <Link
            href="/notifications"
            className={cn(DASHBOARD_ACTION_LINK_BASE_CLASS, 'text-sm text-matrix-green hover:border-matrix-green/40', DASHBOARD_FOCUS_RING_CLASS)}
          >
            {t('nextActions.notifications')}
          </Link>
        </div>
      </article>
    </section>
  );
}
