import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ReferralPage from '../page';

vi.mock('@/widgets/referral-cabinet/referral-cabinet-dashboard', () => ({
  ReferralCabinetDashboard: () => <div>live referral cabinet</div>,
}));

describe('ReferralPage', () => {
  it('renders the live referral/gift cabinet when growth surfaces are enabled', () => {
    render(<ReferralPage />);

    expect(screen.getByText('live referral cabinet')).toBeInTheDocument();
  });
});
