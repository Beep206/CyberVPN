import { describe, expect, it, vi } from 'vitest';
import LegacyAdminRoutesLayout from '../layout';

vi.mock('next/navigation', () => ({
  redirect: vi.fn(() => {
    throw new Error('NEXT_REDIRECT');
  }),
}));

const { redirect } = await import('next/navigation');

describe('legacy admin routes layout', () => {
  it('keeps legacy admin routes retired even when proxy fallback is bypassed', async () => {
    await expect(
      LegacyAdminRoutesLayout({
        children: <div>legacy admin content</div>,
        params: Promise.resolve({ locale: 'en-EN' }),
      }),
    ).rejects.toThrow('NEXT_REDIRECT');

    expect(redirect).toHaveBeenCalledWith('/en-EN/dashboard');
  });
});
