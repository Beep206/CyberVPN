import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  requestUserConnections,
  getUserConnections,
  requestNodeConnections,
  getNodeConnections,
  dropConnections,
  listUnresolvedDropReceipts,
  getDropReceipt,
  reconcileDropReceipt,
} = vi.hoisted(() => ({
  requestUserConnections: vi.fn(),
  getUserConnections: vi.fn(),
  requestNodeConnections: vi.fn(),
  getNodeConnections: vi.fn(),
  dropConnections: vi.fn(),
  listUnresolvedDropReceipts: vi.fn(),
  getDropReceipt: vi.fn(),
  reconcileDropReceipt: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-EN',
  useTranslations: () => (
    key: string,
    values?: Record<string, string | number>,
  ) => values ? `${key}:${Object.values(values).join(':')}` : key,
}));

vi.mock('@/lib/api/remnawave-connections', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-connections')>();
  return {
    ...actual,
    adminRemnawaveConnectionsApi: {
      requestUserConnections,
      getUserConnections,
      requestNodeConnections,
      getNodeConnections,
      dropConnections,
      listUnresolvedDropReceipts,
      getDropReceipt,
      reconcileDropReceipt,
    },
  };
});

import { RemnawaveConnectionsConsole } from './remnawave-connections-console';

const REQUEST_ID = 'a'.repeat(43);
const RECEIPT_ID = 'b'.repeat(43);
const NODE_UUID = '550e8400-e29b-41d4-a716-446655440000';
const CAPABILITIES = {
  read_connections: true,
  drop_connections: true,
  drop_requires_idempotency_key: true,
  drop_outcome_may_be_unknown: true,
};
const REQUEST = {
  request_id: REQUEST_ID,
  poll_after_seconds: 1,
  expires_in_seconds: 300,
  capabilities: CAPABILITIES,
};

function renderConsole() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RemnawaveConnectionsConsole />
    </QueryClientProvider>,
  );
}

describe('RemnawaveConnectionsConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('crypto', { randomUUID: () => '550e8400-e29b-41d4-a716-446655440099' });
    requestUserConnections.mockResolvedValue(REQUEST);
    requestNodeConnections.mockResolvedValue(REQUEST);
    getUserConnections.mockResolvedValue({
      is_completed: true,
      is_failed: false,
      progress: { total: 1, completed: 1, percent: 100 },
      result: {
        success: true,
        user_id: 42,
        nodes: [{
          node_uuid: NODE_UUID,
          node_name: 'Moscow edge',
          country_code: 'RU',
          ips: [{ ip: '203.0.113.10', last_seen: '2026-08-31T10:00:00Z' }],
        }],
      },
      capabilities: CAPABILITIES,
    });
    getNodeConnections.mockResolvedValue({
      is_completed: true,
      is_failed: false,
      result: {
        success: true,
        node_uuid: NODE_UUID,
        users: [{
          user_id: 42,
          ips: [{ ip: '203.0.113.10', last_seen: '2026-08-31T10:00:00Z' }],
        }],
      },
      capabilities: CAPABILITIES,
    });
    dropConnections.mockResolvedValue({
      expires_at: null,
      expires_in_seconds: null,
      receipt_id: RECEIPT_ID,
      requires_reconciliation: true,
      state: 'outcome_unknown',
      retry_allowed: false,
    });
    listUnresolvedDropReceipts.mockResolvedValue({ items: [], next_cursor: null });
  });

  it('starts with explicit empty states and keeps drop unavailable until capability verification', () => {
    renderConsole();

    expect(screen.getByText('states.userEmpty')).toHaveAttribute('role', 'status');
    expect(screen.getByText('states.nodeEmpty')).toHaveAttribute('role', 'status');
    expect(screen.getByText('drop.capabilityUnverified').closest('[role="status"]')).not.toBeNull();
    expect(screen.queryByRole('button', { name: 'drop.action' })).not.toBeInTheDocument();
  });

  it('requests and polls by numeric user ID, then renders admin-only IP topology', async () => {
    const user = userEvent.setup();
    renderConsole();

    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));

    expect(await screen.findByText('203.0.113.10')).toBeInTheDocument();
    expect(screen.getByText('Moscow edge')).toBeInTheDocument();
    expect(screen.getByText(NODE_UUID)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'tables.userCaption' })).toBeInTheDocument();
    expect(requestUserConnections).toHaveBeenCalledWith(42);
    expect(getUserConnections).toHaveBeenCalledWith(42, REQUEST_ID);
    expect(screen.getByRole('button', { name: 'drop.action' })).toBeEnabled();
  });

  it('requests and polls by node UUID, then renders numeric users and their IPs', async () => {
    const user = userEvent.setup();
    renderConsole();

    await user.type(screen.getByLabelText('node.label'), NODE_UUID);
    await user.click(screen.getByRole('button', { name: 'actions.inspectNode' }));

    const table = await screen.findByRole('table', { name: 'tables.nodeCaption' });
    expect(within(table).getByText('42')).toBeInTheDocument();
    expect(within(table).getByText('203.0.113.10')).toBeInTheDocument();
    expect(requestNodeConnections).toHaveBeenCalledWith(NODE_UUID);
    expect(getNodeConnections).toHaveBeenCalledWith(NODE_UUID, REQUEST_ID);
  });

  it('shows a pending request without exposing stale success state', async () => {
    requestUserConnections.mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderConsole();

    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));

    expect(screen.getByRole('button', { name: 'states.requesting' })).toBeDisabled();
    expect(screen.queryByText('203.0.113.10')).not.toBeInTheDocument();
  });

  it.each([
    [403, 'errors.forbidden'],
    [404, 'errors.expired'],
    [409, 'errors.conflict'],
    [422, 'errors.validation'],
    [502, 'errors.invalidProviderResponse'],
    [503, 'errors.unavailable'],
  ])('renders the explicit %s request state', async (status, key) => {
    requestUserConnections.mockRejectedValue({ response: { status } });
    const user = userEvent.setup();
    renderConsole();

    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(key);
    const retry = screen.getByRole('button', { name: 'actions.retryRead' });
    if (status === 403) expect(retry).toBeDisabled();
    else expect(retry).toBeEnabled();
  });

  it('renders a completed empty user result explicitly', async () => {
    getUserConnections.mockResolvedValue({
      is_completed: true,
      is_failed: false,
      progress: { total: 1, completed: 1, percent: 100 },
      result: { success: true, user_id: 42, nodes: [] },
      capabilities: CAPABILITIES,
    });
    const user = userEvent.setup();
    renderConsole();

    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));

    expect(await screen.findByText('states.noUserConnections')).toHaveAttribute('role', 'status');
  });

  it('submits a confirmed drop once with a stable local idempotency key and no retry action', async () => {
    const user = userEvent.setup();
    renderConsole();
    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));
    await screen.findByText('203.0.113.10');

    await user.type(screen.getByLabelText('drop.userIdsLabel'), '42');
    await user.click(screen.getByRole('checkbox', { name: 'drop.confirm' }));
    await user.click(screen.getByRole('button', { name: 'drop.action' }));

    expect(await screen.findByText('drop.receipt.outcome_unknown')).toBeInTheDocument();
    expect(dropConnections).toHaveBeenCalledTimes(1);
    expect(dropConnections).toHaveBeenCalledWith(
      {
        dropBy: { by: 'userIds', userIds: [42] },
        targetNodes: { target: 'allNodes' },
      },
      'connections-drop:550e8400-e29b-41d4-a716-446655440099',
    );
    expect(screen.getByRole('button', { name: 'drop.action' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument();
  });

  it('associates bounded drop validation with the invalid target control', async () => {
    const user = userEvent.setup();
    renderConsole();
    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));
    await screen.findByText('203.0.113.10');

    await user.click(screen.getByRole('button', { name: 'drop.action' }));

    expect(screen.getByRole('alert')).toHaveTextContent('drop.validation');
    expect(screen.getByLabelText('drop.userIdsLabel')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('drop.userIdsLabel')).toHaveAttribute(
      'aria-describedby',
      'remnawave-drop-values-help remnawave-drop-error',
    );
    expect(dropConnections).not.toHaveBeenCalled();
  });

  it('allows only an explicit same-key replay after 503 and blocks a new-key resubmit', async () => {
    dropConnections.mockRejectedValue({ response: { status: 503 } });
    const user = userEvent.setup();
    renderConsole();
    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));
    await screen.findByText('203.0.113.10');

    const targets = screen.getByLabelText('drop.userIdsLabel');
    await user.type(targets, '42');
    await user.click(screen.getByRole('checkbox', { name: 'drop.confirm' }));
    await user.click(screen.getByRole('button', { name: 'drop.action' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('errors.unavailable');
    expect(screen.getByRole('button', { name: 'drop.action' })).toBeDisabled();
    expect(dropConnections).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'drop.retrySameKey' }));
    expect(dropConnections).toHaveBeenCalledTimes(2);
    expect(dropConnections.mock.calls[1]).toEqual(dropConnections.mock.calls[0]);

    await user.clear(targets);
    await user.type(targets, '43');
    await user.clear(targets);
    await user.type(targets, '42');
    await user.click(screen.getByRole('checkbox', { name: 'drop.confirm' }));
    await user.click(screen.getByRole('button', { name: 'drop.action' }));

    expect(screen.getByRole('alert')).toHaveTextContent('drop.alreadyAttempted');
    expect(dropConnections).toHaveBeenCalledTimes(2);
  });

  it('keeps drop explicitly unavailable when the backend omits the safe capability', async () => {
    requestUserConnections.mockResolvedValue({
      ...REQUEST,
      capabilities: { ...CAPABILITIES, drop_connections: false },
    });
    const user = userEvent.setup();
    renderConsole();

    await user.type(screen.getByLabelText('user.label'), '42');
    await user.click(screen.getByRole('button', { name: 'actions.inspectUser' }));

    await waitFor(() => expect(requestUserConnections).toHaveBeenCalledTimes(1));
    expect(screen.getByText('drop.capabilityUnavailable').closest('[role="status"]')).not.toBeNull();
    expect(screen.queryByRole('button', { name: 'drop.action' })).not.toBeInTheDocument();
  });
});
