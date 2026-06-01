import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RewardsCodesPage from '../codes/page';
import RewardsGiftsPage from '../gifts/page';
import RewardsInvitesPage from '../invites/page';
import RewardsNotificationsPage from '../notifications/page';
import RewardsPage from '../page';
import RewardsReferralPage from '../referral/page';

const { dashboardMock } = vi.hoisted(() => ({
  dashboardMock: vi.fn(({ view }: { view: string }) => (
    <div data-testid="rewards-dashboard" data-view={view} />
  )),
}));

vi.mock('@/widgets/referral-cabinet/referral-cabinet-dashboard', () => ({
  ReferralCabinetDashboard: dashboardMock,
}));

describe('rewards routes', () => {
  beforeEach(() => {
    dashboardMock.mockClear();
  });

  it.each([
    ['overview', RewardsPage, 'overview'],
    ['referral', RewardsReferralPage, 'referral'],
    ['gifts', RewardsGiftsPage, 'gifts'],
    ['invites', RewardsInvitesPage, 'invites'],
    ['codes', RewardsCodesPage, 'codes'],
    ['notifications', RewardsNotificationsPage, 'notifications'],
  ])('renders the %s route with its rewards view', (_name, Page, view) => {
    render(<Page />);

    expect(screen.getByTestId('rewards-dashboard')).toHaveAttribute(
      'data-view',
      view,
    );
    expect(dashboardMock).toHaveBeenCalledTimes(1);
    expect(dashboardMock.mock.calls[0]?.[0]).toEqual({ view });
  });
});
