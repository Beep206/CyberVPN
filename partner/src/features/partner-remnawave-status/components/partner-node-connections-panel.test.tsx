import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  dropNodeConnectionsByServiceIdentity,
  getNodeConnections,
  requestNodeConnections,
} = vi.hoisted(() => ({
  dropNodeConnectionsByServiceIdentity: vi.fn(),
  getNodeConnections: vi.fn(),
  requestNodeConnections: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en',
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/lib/api/remnawave-connections', () => ({
  partnerRemnawaveConnectionsApi: {
    dropNodeConnectionsByServiceIdentity,
    getNodeConnections,
    requestNodeConnections,
  },
}));

import { PartnerNodeConnectionsPanel } from './partner-node-connections-panel';

const NODE_UUID = '11111111-1111-1111-1111-111111111111';
const SERVICE_IDENTITY_UUID = '22222222-2222-4222-8222-222222222222';
const REQUEST_ID = 'r'.repeat(43);
const RECEIPT_ID = 'p'.repeat(43);
const CAPABILITIES = {
  read_connections: true,
  drop_connections: true,
  drop_requires_idempotency_key: true,
  drop_outcome_may_be_unknown: true,
};

const READ_REQUEST = {
  request_id: REQUEST_ID,
  poll_after_seconds: 10,
  expires_in_seconds: 300,
  capabilities: CAPABILITIES,
};

const COMPLETED_STATUS = {
  is_completed: true,
  is_failed: false,
  success: true,
  node_uuid: NODE_UUID,
  connected_user_count: 2,
  active_ip_count: 3,
  last_seen_at: '2026-08-31T08:30:00Z',
  capabilities: CAPABILITIES,
};

function renderPanel(overrides: {
  connectionsAvailable?: boolean;
  exactGrantCanExecute?: boolean;
  executableServiceIdentityUuids?: readonly string[];
  roleCanExecute?: boolean;
} = {}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PartnerNodeConnectionsPanel
        workspaceId="workspace-1"
        nodeUuid={NODE_UUID}
        connectionsAvailable={overrides.connectionsAvailable ?? true}
        roleCanExecute={overrides.roleCanExecute ?? true}
        exactGrantCanExecute={overrides.exactGrantCanExecute ?? true}
        executableServiceIdentityUuids={
          overrides.executableServiceIdentityUuids ?? [SERVICE_IDENTITY_UUID]
        }
      />
    </QueryClientProvider>,
  );
}

async function loadSnapshot(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'requestSnapshot' }));
  await waitFor(() => {
    expect(getNodeConnections).toHaveBeenCalledWith('workspace-1', NODE_UUID, REQUEST_ID);
  });
}

describe('PartnerNodeConnectionsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    requestNodeConnections.mockResolvedValue(READ_REQUEST);
    getNodeConnections.mockResolvedValue(COMPLETED_STATUS);
    dropNodeConnectionsByServiceIdentity.mockResolvedValue({
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 86_400,
      receipt_id: RECEIPT_ID,
      requires_reconciliation: false,
      state: 'accepted',
      retry_allowed: false,
    });
  });

  it('disables snapshot requests when the current workspace status denies connections', async () => {
    const user = userEvent.setup();
    renderPanel({ connectionsAvailable: false });

    const button = screen.getByRole('button', { name: 'requestSnapshot' });
    expect(button).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('capabilityUnavailable');
    await user.click(button);
    expect(requestNodeConnections).not.toHaveBeenCalled();
  });

  it('shows an explicit empty state before a read request and a pending state while it is created', async () => {
    requestNodeConnections.mockReturnValue(new Promise(() => undefined));
    const user = userEvent.setup();
    renderPanel();

    expect(screen.getByText('empty')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'requestSnapshot' }));

    expect(screen.getByRole('status')).toHaveTextContent('requestingStatus');
  });

  it('renders only aggregate counts and last-seen time from an exact-node poll', async () => {
    getNodeConnections.mockResolvedValue({
      ...COMPLETED_STATUS,
      users: [{ user_id: 42, ips: ['203.0.113.10'] }],
      node_ip: '203.0.113.11',
      topology: 'private-upstream',
      provider_token: 'must-not-render',
    });
    const user = userEvent.setup();
    renderPanel();

    await loadSnapshot(user);

    expect(await screen.findByText('connectedUsers')).toBeInTheDocument();
    expect(screen.getByText('activeAddresses')).toBeInTheDocument();
    expect(screen.getByText('lastSeen')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.queryByText('42')).not.toBeInTheDocument();
    expect(screen.queryByText('203.0.113.10')).not.toBeInTheDocument();
    expect(screen.queryByText('203.0.113.11')).not.toBeInTheDocument();
    expect(screen.queryByText('private-upstream')).not.toBeInTheDocument();
    expect(screen.queryByText('must-not-render')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ssh/i })).not.toBeInTheDocument();
  });

  it('renders a truthful zero-connections result', async () => {
    getNodeConnections.mockResolvedValue({
      ...COMPLETED_STATUS,
      connected_user_count: 0,
      active_ip_count: 0,
      last_seen_at: null,
    });
    const user = userEvent.setup();
    renderPanel();

    await loadSnapshot(user);

    expect(await screen.findByText('noActiveConnections')).toBeInTheDocument();
    expect(screen.getByText('neverSeen')).toBeInTheDocument();
  });

  it('keeps polling-state and provider-job failure distinct from an empty result', async () => {
    getNodeConnections.mockResolvedValue({
      ...COMPLETED_STATUS,
      is_completed: false,
      success: null,
      connected_user_count: null,
      active_ip_count: null,
      last_seen_at: null,
    });
    const user = userEvent.setup();
    const { unmount } = renderPanel();

    await loadSnapshot(user);
    expect(await screen.findByRole('status')).toHaveTextContent('polling');
    unmount();

    vi.clearAllMocks();
    requestNodeConnections.mockResolvedValue(READ_REQUEST);
    getNodeConnections.mockResolvedValue({
      ...COMPLETED_STATUS,
      is_completed: true,
      is_failed: true,
      success: null,
      connected_user_count: null,
      active_ip_count: null,
      last_seen_at: null,
    });
    renderPanel();
    await loadSnapshot(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('jobFailed.title');
  });

  it.each([
    [403, 'forbidden'],
    [404, 'notFound'],
    [409, 'conflict'],
    [502, 'invalidProvider'],
    [503, 'unavailable'],
  ])('maps request HTTP %i to an accessible %s state', async (status, key) => {
    requestNodeConnections.mockRejectedValue({ response: { status } });
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole('button', { name: 'requestSnapshot' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(`errors.${key}.title`);
  });

  it('treats an expired poll receipt as not found and requests a new scoped snapshot', async () => {
    getNodeConnections.mockRejectedValue({ response: { status: 404 } });
    const user = userEvent.setup();
    renderPanel();

    await loadSnapshot(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('errors.notFound.title');
    await user.click(screen.getByRole('button', { name: 'retry' }));

    await waitFor(() => {
      expect(requestNodeConnections).toHaveBeenCalledTimes(2);
    });
  });

  it('requires remnawave_execute in both the active role and the exact node grant', async () => {
    const user = userEvent.setup();
    const first = renderPanel({ roleCanExecute: false, exactGrantCanExecute: true });
    await loadSnapshot(user);

    expect(await screen.findByText('drop.permissionRequired')).toBeInTheDocument();
    expect(screen.queryByLabelText('drop.serviceIdentityUuidLabel')).not.toBeInTheDocument();
    first.unmount();

    vi.clearAllMocks();
    requestNodeConnections.mockResolvedValue(READ_REQUEST);
    getNodeConnections.mockResolvedValue(COMPLETED_STATUS);
    renderPanel({ roleCanExecute: true, exactGrantCanExecute: false });
    await loadSnapshot(user);

    expect(await screen.findByText('drop.permissionRequired')).toBeInTheDocument();
    expect(screen.queryByLabelText('drop.serviceIdentityUuidLabel')).not.toBeInTheDocument();
  });

  it('validates an opaque target and sends a loaded exact service-identity grant', async () => {
    const user = userEvent.setup();
    renderPanel();
    await loadSnapshot(user);
    const input = await screen.findByLabelText('drop.serviceIdentityUuidLabel');

    expect(screen.getByText('drop.serviceIdentityRequirement')).toBeInTheDocument();
    await user.type(input, 'not-a-uuid');
    await user.click(screen.getByRole('button', { name: 'drop.submit' }));
    expect(screen.getByRole('alert')).toHaveTextContent('drop.serviceIdentityUuidError');
    expect(dropNodeConnectionsByServiceIdentity).not.toHaveBeenCalled();

    await user.clear(input);
    await user.selectOptions(
      screen.getByLabelText('drop.serviceIdentitySelectLabel'),
      SERVICE_IDENTITY_UUID,
    );
    await user.click(screen.getByRole('button', { name: 'drop.submit' }));

    await waitFor(() => {
      expect(dropNodeConnectionsByServiceIdentity).toHaveBeenCalledTimes(1);
    });
    const [workspaceId, nodeUuid, serviceIdentityUuid, idempotencyKey] =
      dropNodeConnectionsByServiceIdentity.mock.calls[0];
    expect(workspaceId).toBe('workspace-1');
    expect(nodeUuid).toBe(NODE_UUID);
    expect(serviceIdentityUuid).toBe(SERVICE_IDENTITY_UUID);
    expect(idempotencyKey).toMatch(/^partner-connection-drop-[A-Za-z0-9-]{16,}$/);
    expect(await screen.findByRole('status')).toHaveTextContent('drop.accepted.title');
  });

  it('accepts a manually entered exact UUID when pagination hides the grant', async () => {
    const user = userEvent.setup();
    renderPanel({ executableServiceIdentityUuids: [] });
    await loadSnapshot(user);

    expect(screen.queryByLabelText('drop.serviceIdentitySelectLabel')).not.toBeInTheDocument();
    await user.type(
      await screen.findByLabelText('drop.serviceIdentityUuidLabel'),
      SERVICE_IDENTITY_UUID,
    );
    await user.click(screen.getByRole('button', { name: 'drop.submit' }));

    await waitFor(() => {
      expect(dropNodeConnectionsByServiceIdentity).toHaveBeenCalledWith(
        'workspace-1',
        NODE_UUID,
        SERVICE_IDENTITY_UUID,
        expect.stringMatching(/^partner-connection-drop-[A-Za-z0-9-]{16,}$/),
      );
    });
  });

  it('reports an upstream outcome_unknown receipt and never offers a retry', async () => {
    dropNodeConnectionsByServiceIdentity.mockResolvedValue({
      expires_at: null,
      expires_in_seconds: null,
      receipt_id: RECEIPT_ID,
      requires_reconciliation: true,
      state: 'outcome_unknown',
      retry_allowed: false,
    });
    const user = userEvent.setup();
    renderPanel();
    await loadSnapshot(user);
    await user.selectOptions(
      await screen.findByLabelText('drop.serviceIdentitySelectLabel'),
      SERVICE_IDENTITY_UUID,
    );
    await user.click(screen.getByRole('button', { name: 'drop.submit' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('drop.outcomeUnknown.title');
    expect(screen.queryByRole('button', { name: 'drop.retrySameKey' })).not.toBeInTheDocument();
    expect(dropNodeConnectionsByServiceIdentity).toHaveBeenCalledTimes(1);
  });

  it('replays an ambiguous browser failure only with the same idempotency key', async () => {
    dropNodeConnectionsByServiceIdentity
      .mockRejectedValueOnce(new Error('browser timeout'))
      .mockResolvedValueOnce({
        expires_at: '2026-09-01T12:00:00Z',
        expires_in_seconds: 86_400,
        receipt_id: RECEIPT_ID,
        requires_reconciliation: false,
        state: 'accepted',
        retry_allowed: false,
      });
    const user = userEvent.setup();
    renderPanel();
    await loadSnapshot(user);
    await user.selectOptions(
      await screen.findByLabelText('drop.serviceIdentitySelectLabel'),
      SERVICE_IDENTITY_UUID,
    );
    await user.click(screen.getByRole('button', { name: 'drop.submit' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('drop.clientOutcomeUnknown.title');
    await user.click(screen.getByRole('button', { name: 'drop.retrySameKey' }));

    await waitFor(() => {
      expect(dropNodeConnectionsByServiceIdentity).toHaveBeenCalledTimes(2);
    });
    expect(dropNodeConnectionsByServiceIdentity.mock.calls[1][3]).toBe(
      dropNodeConnectionsByServiceIdentity.mock.calls[0][3],
    );
  });

  it.each([
    [403, 'forbidden'],
    [404, 'notFound'],
    [409, 'conflict'],
    [502, 'invalidProvider'],
    [503, 'unavailable'],
  ])('maps drop HTTP %i to an accessible %s state', async (status, key) => {
    dropNodeConnectionsByServiceIdentity.mockRejectedValue({ response: { status } });
    const user = userEvent.setup();
    renderPanel();
    await loadSnapshot(user);
    await user.selectOptions(
      await screen.findByLabelText('drop.serviceIdentitySelectLabel'),
      SERVICE_IDENTITY_UUID,
    );
    await user.click(screen.getByRole('button', { name: 'drop.submit' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(`errors.${key}.title`);
  });
});
