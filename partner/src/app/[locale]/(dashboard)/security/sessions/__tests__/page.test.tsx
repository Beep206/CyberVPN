import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const { mockGetSecurityPageMetadata } = vi.hoisted(() => ({
  mockGetSecurityPageMetadata: vi.fn(),
}));

vi.mock('@/features/security/components/security-sessions-console', () => ({
  SecuritySessionsConsole: () => 'SecuritySessionsConsole',
}));

vi.mock('@/features/security/lib/page-metadata', () => ({
  getSecurityPageMetadata: (...args: unknown[]) =>
    mockGetSecurityPageMetadata(...args),
}));

import SecuritySessionsPage, { generateMetadata } from '../page';

describe('partner security sessions route', () => {
  it('renders the security sessions console on the routable partner URL', () => {
    render(<SecuritySessionsPage />);

    expect(screen.getByText('SecuritySessionsConsole')).toBeInTheDocument();
  });

  it('uses sessions metadata for the canonical security sessions route', async () => {
    const metadata = {
      title: 'Security sessions',
    };
    mockGetSecurityPageMetadata.mockResolvedValueOnce(metadata);

    await expect(
      generateMetadata({
        params: Promise.resolve({ locale: 'en-EN' }),
      }),
    ).resolves.toBe(metadata);

    expect(mockGetSecurityPageMetadata).toHaveBeenCalledWith('en-EN', 'sessions');
  });
});
