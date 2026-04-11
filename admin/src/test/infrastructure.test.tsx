/**
 * QUAL-02.1 Infrastructure Verification Test
 *
 * This test file verifies that the test infrastructure is correctly wired:
 * 1. Vitest runs with jsdom environment
 * 2. React Testing Library renders components
 * 3. @testing-library/jest-dom matchers work (toBeInTheDocument, etc.)
 * 4. Path aliases (@/*) resolve correctly
 * 5. MSW intercepts API calls and returns mock data
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { MOCK_USER, MOCK_SERVERS } from './mocks/handlers';

// Import a real component via the path alias to validate alias resolution
import { ServerStatusDot } from '@/shared/ui/atoms/server-status-dot';

// ---------------------------------------------------------------------------
// 1. Component rendering with React Testing Library
// ---------------------------------------------------------------------------

describe('ServerStatusDot', () => {
  it('test_server_status_dot_online_renders_span', () => {
    const { container } = render(<ServerStatusDot status="online" />);
    const outerSpan = container.firstElementChild;

    expect(outerSpan).toBeInTheDocument();
    expect(outerSpan?.tagName).toBe('SPAN');
    // Should contain two inner spans (ping effect + solid dot)
    expect(outerSpan?.children).toHaveLength(2);
  });

  it('test_server_status_dot_each_status_renders_without_error', () => {
    const statuses = ['online', 'offline', 'warning', 'maintenance'] as const;

    for (const status of statuses) {
      const { unmount } = render(<ServerStatusDot status={status} />);
      // Just verifying no render errors occur for each status
      unmount();
    }
  });

  it('test_server_status_dot_custom_classname_applied', () => {
    const { container } = render(
      <ServerStatusDot status="online" className="ml-2" />,
    );
    const outerSpan = container.firstElementChild;
    expect(outerSpan?.className).toContain('ml-2');
  });
});

// ---------------------------------------------------------------------------
// 2. MSW integration -- verifying mock API responses
// ---------------------------------------------------------------------------

describe('MSW API Mocking', () => {
  it('test_msw_auth_me_returns_mock_user', async () => {
    const response = await fetch('http://localhost:8000/api/v1/auth/me');
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.id).toBe(MOCK_USER.id);
    expect(data.email).toBe(MOCK_USER.email);
    expect(data.role).toBe('user');
  });

  it('test_msw_login_success_returns_tokens', async () => {
    const response = await fetch('http://localhost:8000/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'testuser@cybervpn.io',
        password: 'correct_password',
      }),
    });
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.access_token).toBeDefined();
    expect(data.refresh_token).toBeDefined();
    expect(data.token_type).toBe('bearer');
  });

  it('test_msw_login_invalid_password_returns_401', async () => {
    const response = await fetch('http://localhost:8000/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'testuser@cybervpn.io',
        password: 'wrong_password',
      }),
    });
    const data = await response.json();

    expect(response.status).toBe(401);
    expect(data.detail).toBe('Invalid email or password');
  });

  it('test_msw_register_success_returns_unverified_user', async () => {
    const response = await fetch('http://localhost:8000/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        login: 'newuser',
        email: 'new@cybervpn.io',
        password: 'securePass123',
      }),
    });
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.is_active).toBe(false);
    expect(data.is_email_verified).toBe(false);
    expect(data.message).toContain('verify');
  });

  it('test_msw_register_duplicate_email_returns_409', async () => {
    const response = await fetch('http://localhost:8000/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        login: 'taken',
        email: 'taken@cybervpn.io',
        password: 'somePass',
      }),
    });

    expect(response.status).toBe(409);
  });

  it('test_msw_forgot_password_always_returns_success', async () => {
    const response = await fetch(
      'http://localhost:8000/api/v1/auth/forgot-password',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'nonexistent@example.com' }),
      },
    );
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toBeDefined();
  });

  it('test_msw_reset_password_success', async () => {
    const response = await fetch(
      'http://localhost:8000/api/v1/auth/reset-password',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'testuser@cybervpn.io',
          code: '123456',
          new_password: 'newSecurePass',
        }),
      },
    );
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toContain('reset');
  });

  it('test_msw_delete_account_returns_message', async () => {
    const response = await fetch('http://localhost:8000/api/v1/auth/me', {
      method: 'DELETE',
    });
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.message).toBe('Account has been deleted');
  });

  it('test_msw_servers_list_returns_all_servers', async () => {
    const response = await fetch('http://localhost:8000/api/v1/servers');
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(Array.isArray(data)).toBe(true);
    expect(data).toHaveLength(MOCK_SERVERS.length);
    expect(data[0].id).toBe('srv_001');
    expect(data[0].protocol).toBe('wireguard');
  });

  it('test_msw_servers_filter_by_status', async () => {
    const response = await fetch(
      'http://localhost:8000/api/v1/servers?status=online',
    );
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data).toHaveLength(2); // Frankfurt + Amsterdam
    expect(data.every((s: { status: string }) => s.status === 'online')).toBe(
      true,
    );
  });

  it('test_msw_users_list_returns_paginated_users', async () => {
    const response = await fetch('http://localhost:8000/api/v1/users');
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.items).toBeDefined();
    expect(data.total).toBe(4);
    expect(data.page).toBe(1);
  });

  it('test_msw_handler_override_per_test_works', async () => {
    // Override the /auth/me handler just for this test
    server.use(
      http.get('http://localhost:8000/api/v1/auth/me', () => {
        return HttpResponse.json(
          { detail: 'Not authenticated' },
          { status: 401 },
        );
      }),
    );

    const response = await fetch('http://localhost:8000/api/v1/auth/me');
    expect(response.status).toBe(401);

    // After this test, resetHandlers() in afterEach will restore the default
  });

  it('test_msw_default_handler_restored_after_override', async () => {
    // This test runs after the override test above.
    // Thanks to resetHandlers() in afterEach, the default handler is restored.
    const response = await fetch('http://localhost:8000/api/v1/auth/me');
    expect(response.status).toBe(200);

    const data = await response.json();
    expect(data.id).toBe(MOCK_USER.id);
  });
});
