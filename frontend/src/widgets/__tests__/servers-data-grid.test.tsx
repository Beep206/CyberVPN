import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ---------------------------------------------------------------------------
// Module-level mocks (hoisted by Vitest)
// ---------------------------------------------------------------------------

vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text, className }: { text: string; className?: string }) => (
    <span data-testid="cypher-text" className={className}>
      {text}
    </span>
  ),
}));

vi.mock('@/shared/ui/atoms/server-status-dot', () => ({
  ServerStatusDot: ({ status }: { status: string }) => (
    <span data-testid="server-status-dot" data-status={status} />
  ),
}));

vi.mock('@/components/ui/InceptionButton', () => ({
  InceptionButton: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="inception-button">{children}</div>
  ),
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) =>
    args
      .filter(Boolean)
      .map((a) => (typeof a === 'string' ? a : ''))
      .join(' ')
      .trim(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => key;
    return t;
  },
}));

// Import after mocks
import { ServersDataGrid } from '../servers-data-grid';

// ---------------------------------------------------------------------------
// Constants matching the source mockServers
// ---------------------------------------------------------------------------

const MOCK_SERVER_NAMES = [
  'Tokyo Node 01',
  'NYC Core',
  'London Edge',
  'Singapore Stealth',
  'Berlin Stream',
];

const COLUMN_HEADER_KEYS = [
  'columns.serverName',
  'columns.location',
  'columns.ipAddress',
  'columns.protocol',
  'columns.status',
  'columns.load',
  'columns.controls',
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ServersDataGrid', () => {
  // -------------------------------------------------------------------------
  // Basic rendering
  // -------------------------------------------------------------------------

  it('test_renders_title', () => {
    render(<ServersDataGrid />);
    expect(screen.getByText('title')).toBeInTheDocument();
  });

  it('test_renders_deploy_node_button', () => {
    render(<ServersDataGrid />);
    expect(screen.getByText('deployNode')).toBeInTheDocument();
  });

  it('test_renders_table_element', () => {
    render(<ServersDataGrid />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Column headers
  // -------------------------------------------------------------------------

  it('test_renders_all_column_headers', () => {
    render(<ServersDataGrid />);
    for (const key of COLUMN_HEADER_KEYS) {
      expect(screen.getByText(key)).toBeInTheDocument();
    }
  });

  // -------------------------------------------------------------------------
  // Data rows
  // -------------------------------------------------------------------------

  it('test_renders_five_data_rows', () => {
    render(<ServersDataGrid />);
    const rows = screen.getAllByRole('row');
    // 1 header row + 5 data rows
    expect(rows).toHaveLength(6);
  });

  it('test_renders_all_server_names', () => {
    render(<ServersDataGrid />);
    for (const name of MOCK_SERVER_NAMES) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
  });

  it('test_renders_ip_addresses', () => {
    render(<ServersDataGrid />);
    expect(screen.getByText('45.32.12.90')).toBeInTheDocument();
    expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
    expect(screen.getByText('178.2.4.11')).toBeInTheDocument();
    expect(screen.getByText('201.10.3.55')).toBeInTheDocument();
    expect(screen.getByText('88.10.22.1')).toBeInTheDocument();
  });

  it('test_renders_protocols', () => {
    render(<ServersDataGrid />);
    const protocols = screen.getAllByText(/^(vless|wireguard|xhttp)$/);
    expect(protocols.length).toBeGreaterThanOrEqual(5);
  });

  it('test_renders_locations', () => {
    render(<ServersDataGrid />);
    expect(screen.getByText('Japan, Tokyo')).toBeInTheDocument();
    expect(screen.getByText('USA, New York')).toBeInTheDocument();
    expect(screen.getByText('UK, London')).toBeInTheDocument();
    expect(screen.getByText('Singapore')).toBeInTheDocument();
    expect(screen.getByText('Germany, Berlin')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Status dots
  // -------------------------------------------------------------------------

  it('test_renders_server_status_dots', () => {
    render(<ServersDataGrid />);
    const dots = screen.getAllByTestId('server-status-dot');
    expect(dots).toHaveLength(5);
  });

  it('test_status_dot_receives_correct_status_prop', () => {
    render(<ServersDataGrid />);
    const dots = screen.getAllByTestId('server-status-dot');
    const statuses = dots.map((d) => d.getAttribute('data-status'));
    expect(statuses).toContain('online');
    expect(statuses).toContain('warning');
    expect(statuses).toContain('maintenance');
  });

  it('test_renders_status_labels', () => {
    render(<ServersDataGrid />);
    // useTranslations returns key as-is: "status.online", "status.warning", etc.
    expect(screen.getAllByText('status.online')).toHaveLength(3);
    expect(screen.getByText('status.warning')).toBeInTheDocument();
    expect(screen.getByText('status.maintenance')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Load bars
  // -------------------------------------------------------------------------

  it('test_renders_load_percentages', () => {
    render(<ServersDataGrid />);
    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByText('82%')).toBeInTheDocument();
    expect(screen.getByText('23%')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('test_high_load_bar_has_warning_class', () => {
    const { container } = render(<ServersDataGrid />);
    const warningBars = container.querySelectorAll('.bg-server-warning');
    // NYC Core has 82% load (> 80 threshold)
    expect(warningBars.length).toBeGreaterThanOrEqual(1);
  });

  it('test_normal_load_bar_has_green_class', () => {
    const { container } = render(<ServersDataGrid />);
    const greenBars = container.querySelectorAll('.bg-matrix-green');
    // Tokyo (45%), London (23%), Singapore (0%), Berlin (65%) are all ≤ 80
    expect(greenBars.length).toBeGreaterThanOrEqual(4);
  });

  // -------------------------------------------------------------------------
  // Action buttons
  // -------------------------------------------------------------------------

  it('test_renders_action_buttons_per_row', () => {
    render(<ServersDataGrid />);
    // 3 action buttons per row × 5 rows = 15
    const restartButtons = screen.getAllByLabelText('actions.restart');
    const stopButtons = screen.getAllByLabelText('actions.stop');
    const configButtons = screen.getAllByLabelText('actions.config');
    expect(restartButtons).toHaveLength(5);
    expect(stopButtons).toHaveLength(5);
    expect(configButtons).toHaveLength(5);
  });

  it('test_action_buttons_have_title_attributes', () => {
    render(<ServersDataGrid />);
    const restartButtons = screen.getAllByTitle('actions.restart');
    expect(restartButtons).toHaveLength(5);
  });

  it('test_action_buttons_wrapped_in_inception_button', () => {
    render(<ServersDataGrid />);
    const inceptionButtons = screen.getAllByTestId('inception-button');
    // 3 buttons per row × 5 rows = 15
    expect(inceptionButtons).toHaveLength(15);
  });

  // -------------------------------------------------------------------------
  // Sorting
  // -------------------------------------------------------------------------

  it('test_clicking_header_does_not_crash', async () => {
    const user = userEvent.setup();
    render(<ServersDataGrid />);
    const nameHeader = screen.getByText('columns.serverName');
    await user.click(nameHeader);
    // Should not throw, table still renders
    expect(screen.getByRole('table')).toBeInTheDocument();
  });
});
