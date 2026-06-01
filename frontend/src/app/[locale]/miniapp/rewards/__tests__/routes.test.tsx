import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import OverviewPage from '../page';
import CodesPage from '../codes/page';
import GiftsPage from '../gifts/page';
import InvitesPage from '../invites/page';
import NotificationsPage from '../notifications/page';
import ReferralPage from '../referral/page';
import LegacyReferralPage from '../../referral/page';

const rewardsRouteMock = vi.hoisted(() => vi.fn());

vi.mock('../RewardsClient', () => ({
  MiniAppRewardsRoute: ({ view }: { view: string }) => {
    rewardsRouteMock(view);
    return <div data-testid="rewards-route">{view}</div>;
  },
}));

describe('Mini App rewards routes', () => {
  it.each([
    ['overview', OverviewPage],
    ['referral', ReferralPage],
    ['gifts', GiftsPage],
    ['invites', InvitesPage],
    ['codes', CodesPage],
    ['notifications', NotificationsPage],
  ])('renders the %s rewards view', (view, Page) => {
    render(<Page />);

    expect(screen.getByTestId('rewards-route')).toHaveTextContent(view);
    expect(rewardsRouteMock).toHaveBeenLastCalledWith(view);
  });

  it('keeps the legacy referral route as a rewards wrapper', () => {
    render(<LegacyReferralPage />);

    expect(screen.getByTestId('rewards-route')).toHaveTextContent('all');
    expect(rewardsRouteMock).toHaveBeenLastCalledWith('all');
  });
});
