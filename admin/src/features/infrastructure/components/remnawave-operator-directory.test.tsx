import { render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '@/stores/auth-store';
import type { AdminRemnawaveCapabilitiesAndStreams } from '@/lib/api/remnawave-status';
import { RemnawaveOperatorDirectory } from './remnawave-operator-directory';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

const capabilities: AdminRemnawaveCapabilitiesAndStreams['capabilities'] = {
  numeric_user_ids: true,
  connections: true,
  geo_check: true,
  node_integrations: true,
  shared_lists: true,
  node_ssh: true,
  tags: true,
  host_mapper: true,
  root_snippets: true,
  redis_stream_export: true,
};

function setRole(role: 'super_admin' | 'finance') {
  useAuthStore.setState({
    user: {
      id: '00000000-0000-4000-8000-000000000001',
      email: 'admin@example.com',
      login: 'admin',
      role,
      is_active: true,
      is_email_verified: true,
      created_at: '2026-08-30T00:00:00Z',
    },
    isAuthenticated: true,
  });
}

describe('RemnawaveOperatorDirectory', () => {
  beforeEach(() => setRole('super_admin'));

  it('links only to real CyberVPN admin surfaces and exposes the scoped connections console', () => {
    render(<RemnawaveOperatorDirectory capabilities={capabilities} />);

    const links = screen.getAllByRole('link', { name: 'open' });
    expect(links[0]).toHaveAttribute('href', '/customers');
    expect(links).toHaveLength(14);
    expect(
      within(screen.getByText('items.connections.title').closest('article')!).getByRole('link', {
        name: 'open',
      }),
    ).toHaveAttribute('href', '/infrastructure/remnawave/connections');
    expect(
      within(screen.getByText('items.tags.title').closest('article')!).getByRole('link', {
        name: 'open',
      }),
    ).toHaveAttribute('href', '/infrastructure/remnawave/operator');
  });

  it('renders locked states instead of navigable actions for insufficient permissions', () => {
    setRole('finance');
    render(<RemnawaveOperatorDirectory capabilities={capabilities} />);

    expect(screen.getByText('items.hosts.title').closest('article')).toHaveTextContent(
      'states.locked',
    );
    const integrations = screen.getByText('items.integrations.title').closest('article');
    expect(integrations).not.toBeNull();
    expect(integrations).toHaveTextContent('states.locked');
    expect(within(integrations!).queryByRole('link', { name: 'open' })).not.toBeInTheDocument();
  });

  it('keeps a deployed route unavailable when its capability flag is off', () => {
    render(
      <RemnawaveOperatorDirectory
        capabilities={{ ...capabilities, host_mapper: false }}
      />,
    );

    expect(screen.getByText('items.hosts.title').closest('article')).toHaveTextContent(
      'states.disabled',
    );
  });
});
