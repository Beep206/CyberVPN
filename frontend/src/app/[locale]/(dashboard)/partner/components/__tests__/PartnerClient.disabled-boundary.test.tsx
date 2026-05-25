import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { PartnerClient } from '../PartnerClient';

vi.mock('@/shared/lib/stage3-partner-flags', () => ({
  STAGE3_PARTNER_PORTAL_UI_ENABLED: false,
  STAGE3_PARTNER_PORTAL_DISABLED_REASON: 'Partner portal is gated for S3.',
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
};

describe('PartnerClient disabled boundary', () => {
  it('shows a disabled-state boundary instead of partner self-serve controls', () => {
    render(<PartnerClient />, { wrapper: createWrapper() });

    expect(screen.getByText('Partner Portal Locked')).toBeInTheDocument();
    expect(screen.getByText('Partner portal is gated for S3.')).toBeInTheDocument();
    expect(screen.getByText('S3-STAGE-05 disabled boundary')).toBeInTheDocument();
    expect(screen.queryByText('Bind Partner Code')).not.toBeInTheDocument();
  });
});
