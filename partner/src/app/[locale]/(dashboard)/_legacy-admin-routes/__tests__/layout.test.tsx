import { describe, expect, it, vi } from 'vitest';
import LegacyAdminRoutesLayout from '../layout';

vi.mock('next/navigation', () => ({
  redirect: vi.fn(() => {
    throw new Error('NEXT_REDIRECT');
  }),
}));

vi.mock('@/features/storefront-shell/lib/server-surface-context', () => ({
  getPartnerSurfaceContext: vi.fn(),
}));

const { redirect } = await import('next/navigation');
const { getPartnerSurfaceContext } = await import('@/features/storefront-shell/lib/server-surface-context');

describe('legacy admin routes layout', () => {
  it('redirects partner surfaces away from legacy admin-only routes', async () => {
    vi.mocked(getPartnerSurfaceContext).mockResolvedValue({
      family: 'portal',
      host: 'portal.localhost:3002',
      brandName: 'Ozoxy Partner Portal',
      brandLabel: 'Ozoxy Partner Portal',
      authRealmKey: 'partner',
      routes: {
        login: '/login',
      },
    });

    await expect(
      LegacyAdminRoutesLayout({
        children: <div>legacy admin content</div>,
        params: Promise.resolve({ locale: 'en-EN' }),
      }),
    ).rejects.toThrow('NEXT_REDIRECT');

    expect(redirect).toHaveBeenCalledWith('/en-EN/dashboard');
  });
});
