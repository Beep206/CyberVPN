import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import {
  createPartnerPortalScenarioState,
  type PartnerPortalState,
} from '@/features/partner-portal-state/lib/portal-state';

const mockRuntimeState = vi.fn<
  () => {
    state: PartnerPortalState;
    isCanonicalWorkspace: boolean;
    activeWorkspace: null;
    notificationPreferences: null;
    queries: Record<string, null>;
  }
>(() => ({
  state: createPartnerPortalScenarioState(
    'active',
    'creator_affiliate',
    'workspace_owner',
    'R2',
  ),
  isCanonicalWorkspace: false,
  activeWorkspace: null,
  notificationPreferences: null,
  queries: {},
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
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

import { PartnerRouteGuard } from './partner-route-guard';

describe('PartnerRouteGuard', () => {
  it('explains release-ring blocks through dashboard and inbox actions', () => {
    mockRuntimeState.mockReturnValue({
      state: createPartnerPortalScenarioState(
        'active',
        'creator_affiliate',
        'workspace_owner',
        'R1',
      ),
      isCanonicalWorkspace: false,
      activeWorkspace: null,
      notificationPreferences: null,
      queries: {},
    });

    render(
      <PartnerRouteGuard route="conversions" title="Conversions">
        {(access) => <div>access:{access}</div>}
      </PartnerRouteGuard>,
    );

    expect(screen.getByText('sectionAccess.releaseRingBlockedDescription')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'sectionAccess.dashboardLink' })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: 'sectionAccess.notificationsLink' })).toHaveAttribute('href', '/notifications');
    expect(screen.queryByText('access:read')).not.toBeInTheDocument();
  });

  it('explains role blocks through dashboard and settings actions', () => {
    mockRuntimeState.mockReturnValue({
      state: createPartnerPortalScenarioState(
        'approved_probation',
        'creator_affiliate',
        'analyst',
        'R4',
      ),
      isCanonicalWorkspace: false,
      activeWorkspace: null,
      notificationPreferences: null,
      queries: {},
    });

    render(
      <PartnerRouteGuard route="team" title="Team & Access">
        {(access) => <div>access:{access}</div>}
      </PartnerRouteGuard>,
    );

    expect(screen.getByText('sectionAccess.roleBlockedDescription')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'sectionAccess.settingsLink' })).toHaveAttribute('href', '/settings');
    expect(screen.queryByRole('link', { name: 'sectionAccess.notificationsLink' })).not.toBeInTheDocument();
    expect(screen.queryByText('access:write')).not.toBeInTheDocument();
  });
});
