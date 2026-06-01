import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MiniAppVpnPage from '../page';

vi.mock('next-intl/server', () => ({
  getTranslations: async () => (key: string) => key,
}));

vi.mock('../../components/VpnConfigCard', () => ({
  VpnConfigCard: ({ page }: { page: string }) => (
    <div data-testid="vpn-config-card" data-page={page}>
      VPN config
    </div>
  ),
}));

describe('MiniAppVpnPage', () => {
  it('renders the dedicated VPN access surface', async () => {
    const page = await MiniAppVpnPage({
      params: Promise.resolve({ locale: 'en-EN' }),
    });

    render(page);

    expect(screen.getByText('eyebrow')).toBeInTheDocument();
    expect(screen.getByText('title')).toBeInTheDocument();
    expect(screen.getByText('description')).toBeInTheDocument();
    expect(screen.getByTestId('vpn-config-card')).toHaveAttribute(
      'data-page',
      'vpn',
    );
  });
});
