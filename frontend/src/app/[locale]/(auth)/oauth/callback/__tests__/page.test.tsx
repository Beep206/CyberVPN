import { describe, it, expect, vi, beforeEach } from 'vitest';
import OAuthCallbackPage from '../page';

vi.mock('next/navigation', () => ({
  redirect: vi.fn(),
}));

const { redirect } = await import('next/navigation');

describe('OAuthCallbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('redirects legacy localized callback route back to login with error marker', async () => {
    await OAuthCallbackPage({
      params: Promise.resolve({ locale: 'ru-RU' }),
    });

    expect(redirect).toHaveBeenCalledWith('/ru-RU/login?oauth_error=deprecated_callback');
  });
});
