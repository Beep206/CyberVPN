import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { ServersDataGrid } from '../servers-data-grid';

vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text }: { text: string }) => <span>{text}</span>,
}));

vi.mock('@/shared/ui/atoms/server-status-dot', () => ({
  ServerStatusDot: ({ status }: { status: string }) => (
    <span data-testid="server-status-dot" data-status={status} />
  ),
}));

vi.mock('@/components/ui/InceptionButton', () => ({
  InceptionButton: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/features/servers/hooks/useServers', () => ({
  useServers: () => ({
    data: [
      {
        id: 'srv-1',
        name: 'Tokyo Node 01',
        location: 'Japan, Tokyo',
        ip: '45.32.12.90',
        protocol: 'wireguard',
        status: 'online',
        load: 45,
        uptime: '12d 4h',
        clients: 128,
      },
      {
        id: 'srv-2',
        name: 'NYC Core',
        location: 'USA, New York',
        ip: '192.168.1.1',
        protocol: 'vless',
        status: 'warning',
        load: 82,
        uptime: '4d 2h',
        clients: 93,
      },
    ],
    isPending: false,
    error: null,
  }),
}));

describe('ServersDataGrid', () => {
  it('renders a mobile data list path for narrow layouts', () => {
    render(<ServersDataGrid />);

    const mobileList = screen.getByTestId('servers-mobile-list');

    expect(mobileList).toBeInTheDocument();
    expect(within(mobileList).getByText('Tokyo Node 01')).toBeInTheDocument();
    expect(within(mobileList).getByText('Japan, Tokyo')).toBeInTheDocument();
  });

  it('keeps the dense table as a desktop-only fallback', () => {
    render(<ServersDataGrid />);

    expect(screen.getByTestId('servers-desktop-table').className).toContain(
      'hidden md:block',
    );
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('wraps toolbar controls instead of forcing horizontal compression', () => {
    render(<ServersDataGrid />);

    expect(screen.getByTestId('servers-grid-toolbar').className).toContain(
      'flex-col',
    );
    expect(screen.getByTestId('servers-grid-toolbar').className).toContain(
      'sm:flex-row',
    );
  });
});
