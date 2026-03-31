/**
 * Staging-oriented auth E2E specifications.
 *
 * These tests intentionally remain skip-marked until a browser-based E2E
 * harness with real provider credentials is wired in. The scenarios document
 * the current BFF OAuth contract and must stay aligned with production flows.
 */

import { describe, it } from 'vitest';

describe('Web OAuth BFF flow', () => {
  it.skip('Google start route redirects to /api/oauth/start/google and sets signed oauth_tx cookie', () => {
    // Render the localized login page.
    // Click the Google button.
    // Assert the browser navigates to /api/oauth/start/google with locale and return_to.
    // Assert no sessionStorage state is written for OAuth CSRF data.
    // Assert the provider redirect includes the backend-generated state value.
  });

  it.skip('GitHub callback forwards backend auth cookies and lands on the requested dashboard route', () => {
    // Start login via /api/oauth/start/github.
    // Complete the provider callback through /api/oauth/callback/github.
    // Assert auth cookies are present and the browser lands on the original return_to path.
    // Assert the signed oauth_tx cookie is cleared after callback consumption.
  });

  it.skip('OAuth callback with denied consent redirects to localized login with stable provider_denied code', () => {
    // Complete the provider callback with error=access_denied.
    // Assert redirect to /{locale}/login?oauth_error=provider_denied&oauth_provider={provider}.
    // Assert the login screen renders a user-safe, provider-agnostic error message.
  });

  it.skip('OAuth callback with account collision redirects to localized login with oauth_linking_required code', () => {
    // Simulate backend 409 response for untrusted auto-link.
    // Assert the user is not logged in and is shown the collision/linking-required UX.
  });

  it.skip('OAuth callback that requires 2FA redirects to localized login challenge flow', () => {
    // Simulate backend callback response with requires_2fa=true and tfa_token.
    // Assert redirect to /{locale}/login?2fa=true&oauth_provider={provider}.
    // Assert pending_2fa cookie is staged and no full auth cookies are established yet.
  });
});

describe('Session restoration after OAuth', () => {
  it.skip('fresh social login restores session on the first protected route without redirect loops', () => {
    // Land on a dashboard route after successful OAuth callback.
    // Assert AuthGuard or AuthSessionBootstrap resolves the session via cookies.
    // Assert no redirect loop occurs through /login or /auth/refresh.
  });

  it.skip('expired session on a protected route redirects to localized login with redirect target preserved', () => {
    // Expire the session cookies, open a protected route, and assert redirect.
    // The redirect target must remain the protected pathname, not an auth route.
  });
});
