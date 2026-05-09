import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ReferralPage from '../page';

vi.mock('@/widgets/referral-cabinet/referral-cabinet-dashboard', () => ({
  ReferralCabinetDashboard: () => <div>live referral cabinet</div>,
}));

describe('ReferralPage', () => {
  it('renders the S1 paused state instead of the referral/gift cabinet by default', () => {
    render(<ReferralPage />);

    expect(screen.getByText('Rewards hub is paused')).toBeInTheDocument();
    expect(screen.getByText(/Public referral, gift, and promo-code flows are disabled/i))
      .toBeInTheDocument();
    expect(screen.queryByText('live referral cabinet')).not.toBeInTheDocument();
  });
});
