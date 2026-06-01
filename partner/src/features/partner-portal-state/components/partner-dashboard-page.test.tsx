import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

type PendingTask = {
  id: string;
  task_key: string;
  tone: string;
  route_slug?: string | null;
  source_kind?: string | null;
  source_id?: string | null;
  notes?: string[];
};

type BlockedReason = {
  code: string;
  severity: string;
  route_slug: string | null;
  notes: string[];
};

type RuntimeState = {
  state: PartnerPortalState;
  isCanonicalWorkspace: boolean;
  isSimulationEnabled: boolean;
  counters: {
    open_review_requests: number;
    open_cases: number;
    unread_notifications: number;
    pending_tasks: number;
  } | null;
  pendingTasks: PendingTask[];
  blockedReasons: BlockedReason[];
};

const mockRuntimeState = vi.fn<() => RuntimeState>();

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (
    key: string,
    values?: Record<string, string | number>,
  ) => {
    if (!values) {
      return key;
    }

    return `${key}:${Object.values(values).join(':')}`;
  },
}));

vi.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-portal-runtime-state', () => ({
  usePartnerPortalRuntimeState: () => mockRuntimeState(),
}));

import { PartnerDashboardPage } from './partner-dashboard-page';

function makeRuntimeState(overrides: Partial<RuntimeState> = {}): RuntimeState {
  return {
    state: createPartnerPortalScenarioState(
      'active',
      'creator_affiliate',
      'workspace_owner',
      'R4',
    ),
    isCanonicalWorkspace: false,
    isSimulationEnabled: false,
    counters: null,
    pendingTasks: [],
    blockedReasons: [],
    ...overrides,
  };
}

function getLinkByHref(href: string): HTMLAnchorElement {
  const link = screen
    .getAllByRole('link')
    .find((element) => element.getAttribute('href') === href);

  expect(link).toBeDefined();

  return link as HTMLAnchorElement;
}

describe('PartnerDashboardPage', () => {
  beforeEach(() => {
    mockRuntimeState.mockReturnValue(makeRuntimeState());
  });

  it('routes pending task cards to the owning command-center sections', () => {
    mockRuntimeState.mockReturnValue(makeRuntimeState({
      isCanonicalWorkspace: true,
      counters: {
        open_review_requests: 1,
        open_cases: 1,
        unread_notifications: 0,
        pending_tasks: 2,
      },
      pendingTasks: [
        {
          id: 'task-review-business-profile',
          task_key: 'review_request.business_profile',
          tone: 'warning',
          source_kind: 'review_request',
          source_id: 'review_request_001',
        },
        {
          id: 'task-finance-blocked',
          task_key: 'readiness.finance.blocked',
          tone: 'critical',
          route_slug: 'finance',
          source_kind: 'readiness',
          source_id: 'finance',
          notes: ['Finance profile is blocked.'],
        },
      ],
      blockedReasons: [
        {
          code: 'finance_blocked',
          severity: 'critical',
          route_slug: 'finance',
          notes: ['Payout profile is blocked by partner ops.'],
        },
      ],
    }));

    render(<PartnerDashboardPage />);

    expect(screen.getByText('portalState.reviewRequestKinds.business_profile.title')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'taskActions.organization' })).toHaveAttribute('href', '/organization');
    const financeTaskLink = screen.getAllByRole('link', { name: 'taskActions.finance' })[0];

    expect(financeTaskLink).toHaveAttribute('href', '/finance');
    expect(financeTaskLink).toHaveClass('min-h-11', 'focus-visible:ring-2');
    expect(screen.getByText('Payout profile is blocked by partner ops.')).toBeInTheDocument();
  });

  it('renders the visible section map by approved IA groups with lifecycle state labels', () => {
    mockRuntimeState.mockReturnValue(makeRuntimeState({
      state: createPartnerPortalScenarioState(
        'approved_probation',
        'creator_affiliate',
        'workspace_owner',
        'R4',
      ),
    }));

    render(<PartnerDashboardPage />);

    expect(screen.getByText('sections.groups.onboarding.title')).toBeInTheDocument();
    expect(screen.getByText('sections.groups.promotion.title')).toBeInTheDocument();
    expect(screen.getByText('sections.groups.results.title')).toBeInTheDocument();
    expect(screen.getAllByText('portalState.routeVisibility.limited').length).toBeGreaterThan(0);
    expect(screen.getByText('constraints.limitedTitle')).toBeInTheDocument();

    expect(getLinkByHref('/application')).toHaveClass('focus-visible:ring-2');
  });

  it('explains release-ring held sections before users open blocked routes', () => {
    mockRuntimeState.mockReturnValue(makeRuntimeState({
      state: createPartnerPortalScenarioState(
        'active',
        'creator_affiliate',
        'workspace_owner',
        'R1',
      ),
    }));

    render(<PartnerDashboardPage />);

    expect(screen.getByText('constraints.releaseRingTitle')).toBeInTheDocument();
    expect(screen.getByText(/constraints.releaseRingDescription:/)).toBeInTheDocument();
    const notificationsConstraintLink = screen.getAllByRole('link', { name: 'taskActions.notifications' })[0];
    const nextActionLink = screen.getByRole('link', { name: 'nextActions.application' });

    expect(notificationsConstraintLink).toHaveAttribute('href', '/notifications');
    expect(notificationsConstraintLink).toHaveClass('min-h-11', 'focus-visible:ring-2');
    expect(nextActionLink).toHaveClass('min-h-11', 'focus-visible:ring-2');
  });
});
