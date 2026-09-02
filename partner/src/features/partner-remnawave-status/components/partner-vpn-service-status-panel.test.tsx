import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  dropNodeConnectionsByServiceIdentity,
  getNodeConnections,
  getWorkspaceResource,
  getWorkspaceStatus,
  globalServerList,
  globalServerStats,
  listWorkspaceResources,
  refetchWorkspaces,
  requestNodeConnections,
  workspaceSelection,
} = vi.hoisted(() => ({
  dropNodeConnectionsByServiceIdentity: vi.fn(),
  getNodeConnections: vi.fn(),
  getWorkspaceResource: vi.fn(),
  getWorkspaceStatus: vi.fn(),
  globalServerList: vi.fn(),
  globalServerStats: vi.fn(),
  listWorkspaceResources: vi.fn(),
  refetchWorkspaces: vi.fn(),
  requestNodeConnections: vi.fn(),
  workspaceSelection: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en',
  useTranslations: () => (
    key: string,
    values?: Record<string, string | number>,
  ) => values ? `${key}:${Object.values(values).join(':')}` : key,
}));

vi.mock('@/features/partner-portal-state/lib/use-partner-workspace-selection', () => ({
  usePartnerWorkspaceSelection: () => workspaceSelection(),
}));

vi.mock('@/lib/api/remnawave-status', () => ({
  partnerRemnawaveStatusApi: {
    getWorkspaceResource,
    getWorkspaceStatus,
    listWorkspaceResources,
  },
}));

vi.mock('@/lib/api/remnawave-connections', () => ({
  partnerRemnawaveConnectionsApi: {
    dropNodeConnectionsByServiceIdentity,
    getNodeConnections,
    requestNodeConnections,
  },
}));

vi.mock('@/lib/api/servers', () => ({
  serversApi: {
    getStats: globalServerStats,
    list: globalServerList,
  },
}));

import { PartnerVpnServiceStatusPanel } from './partner-vpn-service-status-panel';

function selection(overrides: Record<string, unknown> = {}) {
  return {
    activeWorkspace: {
      id: 'workspace-1',
      current_permission_keys: ['workspace_read', 'remnawave_read'],
    },
    activeWorkspaceId: 'workspace-1',
    isSwitching: false,
    workspacesQuery: {
      isError: false,
      isPending: false,
      refetch: refetchWorkspaces,
    },
    ...overrides,
  };
}

function renderPanel(ui: ReactNode = <PartnerVpnServiceStatusPanel />) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

const NODE_UUID = '11111111-1111-1111-1111-111111111111';

function mockInspectableNode() {
  workspaceSelection.mockReturnValue(selection({
    activeWorkspace: {
      id: 'workspace-1',
      current_permission_keys: [
        'workspace_read',
        'remnawave_read',
        'remnawave_execute',
      ],
    },
  }));
  listWorkspaceResources.mockResolvedValue({
    workspace_id: 'workspace-1',
    items: [{
      workspace_id: 'workspace-1',
      resource_type: 'node',
      resource_uuid: NODE_UUID,
      effective_permissions: ['remnawave_read', 'remnawave_execute'],
      available_operations: ['inspect_assignment'],
      unavailable_operations: ['mutate_resource', 'execute_resource'],
      forbidden_operations: ['browser_ssh'],
      provider_details_available: false,
      safe_mutations: [],
    }],
    total: 1,
    next_offset: null,
    capabilities: {
      inspect_assignment: true,
      mutate_resource: false,
      execute_resource: false,
      browser_ssh: false,
      mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
      safe_mutations: [],
    },
  });
  getWorkspaceResource.mockResolvedValue({
    workspace_id: 'workspace-1',
    resource_type: 'node',
    resource_uuid: NODE_UUID,
    effective_permissions: ['remnawave_read', 'remnawave_execute'],
    available_operations: ['inspect_assignment'],
    unavailable_operations: ['mutate_resource', 'execute_resource'],
    forbidden_operations: ['browser_ssh'],
    provider_details_available: false,
    safe_mutations: [],
  });
}

async function inspectNode(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'resources.inspect' }));
  return screen.findByRole('button', { name: 'requestSnapshot' });
}

describe('PartnerVpnServiceStatusPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspaceSelection.mockReturnValue(selection());
    getWorkspaceStatus.mockResolvedValue({
      workspace_id: 'workspace-1',
      capabilities: { connections: true, usage: true, devices: false },
      assigned_resources: 3,
      degraded: false,
      degraded_reason: null,
    });
    listWorkspaceResources.mockResolvedValue({
      workspace_id: 'workspace-1',
      items: [],
      total: 0,
      next_offset: null,
      capabilities: {
        inspect_assignment: true,
        mutate_resource: false,
        execute_resource: false,
        browser_ssh: false,
        mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
        safe_mutations: [],
      },
    });
    getWorkspaceResource.mockResolvedValue({
      workspace_id: 'workspace-1',
      resource_type: 'node',
      resource_uuid: '11111111-1111-1111-1111-111111111111',
      effective_permissions: ['remnawave_read'],
      available_operations: ['inspect_assignment'],
      unavailable_operations: ['mutate_resource', 'execute_resource'],
      forbidden_operations: ['browser_ssh'],
      provider_details_available: false,
      safe_mutations: [],
    });
    requestNodeConnections.mockResolvedValue({
      request_id: 'r'.repeat(43),
      poll_after_seconds: 10,
      expires_in_seconds: 300,
      capabilities: {
        read_connections: true,
        drop_connections: true,
        drop_requires_idempotency_key: true,
        drop_outcome_may_be_unknown: true,
      },
    });
    getNodeConnections.mockResolvedValue({
      is_completed: true,
      is_failed: false,
      success: true,
      node_uuid: '11111111-1111-1111-1111-111111111111',
      connected_user_count: 0,
      active_ip_count: 0,
      last_seen_at: null,
      capabilities: {
        read_connections: true,
        drop_connections: true,
        drop_requires_idempotency_key: true,
        drop_outcome_may_be_unknown: true,
      },
    });
  });

  it('enables an exact-node snapshot only when the current workspace status allows connections', async () => {
    mockInspectableNode();
    const user = userEvent.setup();
    renderPanel();

    const requestButton = await inspectNode(user);
    expect(requestButton).toBeEnabled();
    await user.click(requestButton);

    await waitFor(() => {
      expect(requestNodeConnections).toHaveBeenCalledWith('workspace-1', NODE_UUID);
    });
    expect(getWorkspaceStatus).toHaveBeenCalledWith('workspace-1');
    expect(listWorkspaceResources).toHaveBeenCalledWith('workspace-1', 0);
    expect(globalServerList).not.toHaveBeenCalled();
    expect(globalServerStats).not.toHaveBeenCalled();
  });

  it('disables exact-node snapshots when the current workspace status denies connections', async () => {
    mockInspectableNode();
    getWorkspaceStatus.mockResolvedValueOnce({
      workspace_id: 'workspace-1',
      capabilities: { connections: false, usage: true, devices: true },
      assigned_resources: 1,
      degraded: false,
      degraded_reason: null,
    });
    const user = userEvent.setup();
    renderPanel();

    const requestButton = await inspectNode(user);
    expect(requestButton).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('capabilityUnavailable');
    await user.click(requestButton);
    expect(requestNodeConnections).not.toHaveBeenCalled();
  });

  it('disables exact-node snapshots when connections=true conflicts with degraded status', async () => {
    mockInspectableNode();
    getWorkspaceStatus.mockResolvedValueOnce({
      workspace_id: 'workspace-1',
      capabilities: { connections: true, usage: true, devices: true },
      assigned_resources: 1,
      degraded: true,
      degraded_reason: 'internal-node-secret',
    });
    const user = userEvent.setup();
    renderPanel();

    const requestButton = await inspectNode(user);
    expect(requestButton).toBeDisabled();
    expect(screen.getByText('capabilityUnavailable')).toBeInTheDocument();
    expect(screen.queryByText('internal-node-secret')).not.toBeInTheDocument();
    await user.click(requestButton);
    expect(requestNodeConnections).not.toHaveBeenCalled();
  });

  it('does not expose a snapshot request while the current workspace status is pending', async () => {
    mockInspectableNode();
    getWorkspaceStatus.mockReturnValueOnce(new Promise(() => undefined));

    renderPanel();

    expect(screen.getByRole('status')).toHaveTextContent('loading');
    expect(screen.queryByRole('button', { name: 'requestSnapshot' })).not.toBeInTheDocument();
    expect(requestNodeConnections).not.toHaveBeenCalled();
  });

  it('disables exact-node snapshots when the current workspace status errors', async () => {
    mockInspectableNode();
    getWorkspaceStatus.mockRejectedValueOnce(new Error('status unavailable'));
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByRole('alert')).toHaveTextContent('error.title');
    const requestButton = await inspectNode(user);
    expect(requestButton).toBeDisabled();
    await user.click(requestButton);
    expect(requestNodeConnections).not.toHaveBeenCalled();
  });

  it('fails closed when status data belongs to a different workspace', async () => {
    mockInspectableNode();
    getWorkspaceStatus.mockResolvedValueOnce({
      workspace_id: 'workspace-2',
      capabilities: { connections: true, usage: true, devices: true },
      assigned_resources: 1,
      degraded: false,
      degraded_reason: null,
    });
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByRole('alert')).toHaveTextContent('error.title');
    const requestButton = await inspectNode(user);
    expect(requestButton).toBeDisabled();
    await user.click(requestButton);
    expect(requestNodeConnections).not.toHaveBeenCalled();
  });

  it('does not request data when the active workspace lacks remnawave_read', () => {
    workspaceSelection.mockReturnValue(selection({
      activeWorkspace: {
        id: 'workspace-1',
        current_permission_keys: ['workspace_read'],
      },
    }));

    renderPanel();

    expect(screen.getByText('permission.title')).toBeInTheDocument();
    expect(getWorkspaceStatus).not.toHaveBeenCalled();
    expect(listWorkspaceResources).not.toHaveBeenCalled();
  });

  it('renders loading and empty workspace states', () => {
    workspaceSelection.mockReturnValue(selection({
      activeWorkspace: null,
      activeWorkspaceId: null,
      workspacesQuery: {
        isError: false,
        isPending: true,
        refetch: refetchWorkspaces,
      },
    }));
    const { rerender } = renderPanel();

    expect(screen.getByRole('status')).toHaveTextContent('loading');

    workspaceSelection.mockReturnValue(selection({
      activeWorkspace: null,
      activeWorkspaceId: null,
    }));
    rerender(<QueryClientProvider client={new QueryClient()}><PartnerVpnServiceStatusPanel /></QueryClientProvider>);

    expect(screen.getByText('empty')).toBeInTheDocument();
  });

  it('shows workspace-safe aggregates without leaking control-plane fields or raw reasons', async () => {
    getWorkspaceStatus.mockResolvedValue({
      workspace_id: 'workspace-1',
      capabilities: { connections: true, usage: false, devices: true },
      assigned_resources: 4,
      degraded: true,
      degraded_reason: 'internal-node-203.0.113.9-secret',
      node_ssh: true,
      integration_uuid: '11111111-1111-1111-1111-111111111111',
    });

    renderPanel();

    expect(await screen.findByText('degraded.title')).toBeInTheDocument();
    expect(await screen.findByText('resources.empty')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('capabilities.connections')).toBeInTheDocument();
    expect(screen.queryByText('internal-node-203.0.113.9-secret')).not.toBeInTheDocument();
    expect(screen.queryByText('11111111-1111-1111-1111-111111111111')).not.toBeInTheDocument();
    expect(screen.getByText('resources.sshForbidden')).toBeInTheDocument();
  });

  it('renders a 403 boundary and never falls back to another workspace', async () => {
    getWorkspaceStatus.mockRejectedValue({ response: { status: 403 } });

    renderPanel();

    expect(await screen.findByRole('alert')).toHaveTextContent('forbidden.title');
    expect(getWorkspaceStatus).toHaveBeenCalledWith('workspace-1');
    expect(getWorkspaceStatus).toHaveBeenCalledTimes(1);
  });

  it('retries a transient status failure for the same workspace', async () => {
    getWorkspaceStatus
      .mockRejectedValueOnce(new Error('temporary failure'))
      .mockResolvedValueOnce({
        workspace_id: 'workspace-1',
        capabilities: { connections: true, usage: true, devices: true },
        assigned_resources: 2,
        degraded: false,
        degraded_reason: null,
      });
    const user = userEvent.setup();

    renderPanel();

    expect(await screen.findByRole('alert')).toHaveTextContent('error.title');
    expect(await screen.findByText('resources.empty')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'retry' }));

    await waitFor(() => {
      expect(getWorkspaceStatus).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText('2')).toBeInTheDocument();
  });

  it('inspects only the selected resource in the active workspace', async () => {
    listWorkspaceResources.mockResolvedValue({
      workspace_id: 'workspace-1',
      items: [{
        workspace_id: 'workspace-1',
        resource_type: 'node',
        resource_uuid: '11111111-1111-1111-1111-111111111111',
        effective_permissions: ['remnawave_read', 'remnawave_write'],
        available_operations: ['inspect_assignment'],
        unavailable_operations: ['mutate_resource', 'execute_resource'],
        forbidden_operations: ['browser_ssh'],
        provider_details_available: false,
        safe_mutations: [],
      }],
      total: 1,
      next_offset: null,
      capabilities: {
        inspect_assignment: true,
        mutate_resource: false,
        execute_resource: false,
        browser_ssh: false,
        mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
        safe_mutations: [],
      },
    });
    getWorkspaceResource.mockResolvedValue({
      workspace_id: 'workspace-1',
      resource_type: 'node',
      resource_uuid: '11111111-1111-1111-1111-111111111111',
      effective_permissions: ['remnawave_read', 'remnawave_write'],
      available_operations: ['inspect_assignment'],
      unavailable_operations: ['mutate_resource', 'execute_resource'],
      forbidden_operations: ['browser_ssh'],
      provider_details_available: false,
      safe_mutations: [],
    });
    const user = userEvent.setup();

    renderPanel();

    expect(await screen.findByText('resources.types.node')).toBeInTheDocument();
    expect(screen.getByText('resources.mutationsUnavailable')).toBeInTheDocument();
    expect(screen.getByText('resources.sshForbidden')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ssh/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'resources.inspect' }));

    await waitFor(() => {
      expect(getWorkspaceResource).toHaveBeenCalledWith(
        'workspace-1',
        'node',
        '11111111-1111-1111-1111-111111111111',
      );
    });
    expect(await screen.findByText('resources.detailTitle')).toBeInTheDocument();
    expect(screen.getByText('resources.effectivePermissions:remnawave_read, remnawave_write')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 4, name: 'title' })).toBeInTheDocument();
  });

  it('shows a truthful empty inventory without rendering mutation controls', async () => {
    renderPanel();

    expect(await screen.findByText('resources.empty')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /write|execute|ssh/i })).not.toBeInTheDocument();
    expect(getWorkspaceResource).not.toHaveBeenCalled();
  });

  it('wires the profile-tags form only after role and exact-grant write capability are verified', async () => {
    workspaceSelection.mockReturnValue(selection({
      activeWorkspace: {
        id: 'workspace-1',
        current_permission_keys: ['workspace_read', 'remnawave_read', 'remnawave_write'],
      },
    }));
    const profile = {
      workspace_id: 'workspace-1',
      resource_type: 'profile',
      resource_uuid: '44444444-4444-4444-8444-444444444444',
      effective_permissions: ['remnawave_read', 'remnawave_write'],
      available_operations: ['inspect_assignment', 'mutate_resource'],
      unavailable_operations: ['execute_resource'],
      forbidden_operations: ['browser_ssh'],
      provider_details_available: false,
      safe_mutations: ['profile_tags'],
    };
    listWorkspaceResources.mockResolvedValue({
      workspace_id: 'workspace-1',
      items: [profile],
      total: 1,
      next_offset: null,
      capabilities: {
        inspect_assignment: true,
        mutate_resource: true,
        execute_resource: false,
        browser_ssh: false,
        mutation_unavailable_reason: 'limited_to_explicit_profile_and_integration_grants',
        safe_mutations: ['profile_tags'],
      },
    });
    getWorkspaceResource.mockResolvedValue(profile);
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByText('resources.safeMutationsAvailable')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'resources.inspect' }));

    expect(await screen.findByRole('button', { name: 'profile.submit' })).toBeInTheDocument();
    expect(screen.queryByText('integration.title')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ssh|restart|config|topology/i })).not.toBeInTheDocument();
  });

  it('offers only loaded service identities with an effective execute grant', async () => {
    const serviceIdentityUuid = '22222222-2222-4222-8222-222222222222';
    workspaceSelection.mockReturnValue(selection({
      activeWorkspace: {
        id: 'workspace-1',
        current_permission_keys: [
          'workspace_read',
          'remnawave_read',
          'remnawave_execute',
        ],
      },
    }));
    listWorkspaceResources.mockResolvedValue({
      workspace_id: 'workspace-1',
      items: [
        {
          workspace_id: 'workspace-1',
          resource_type: 'node',
          resource_uuid: '11111111-1111-1111-1111-111111111111',
          effective_permissions: ['remnawave_read', 'remnawave_execute'],
          available_operations: ['inspect_assignment'],
          unavailable_operations: ['mutate_resource', 'execute_resource'],
          forbidden_operations: ['browser_ssh'],
          provider_details_available: false,
          safe_mutations: [],
        },
        {
          workspace_id: 'workspace-1',
          resource_type: 'service_identity',
          resource_uuid: serviceIdentityUuid,
          effective_permissions: ['remnawave_read', 'remnawave_execute'],
          available_operations: ['inspect_assignment'],
          unavailable_operations: ['mutate_resource', 'execute_resource'],
          forbidden_operations: ['browser_ssh'],
          provider_details_available: false,
          safe_mutations: [],
        },
        {
          workspace_id: 'workspace-1',
          resource_type: 'service_identity',
          resource_uuid: '33333333-3333-4333-8333-333333333333',
          effective_permissions: ['remnawave_read'],
          available_operations: ['inspect_assignment'],
          unavailable_operations: ['mutate_resource', 'execute_resource'],
          forbidden_operations: ['browser_ssh'],
          provider_details_available: false,
          safe_mutations: [],
        },
      ],
      total: 3,
      next_offset: null,
      capabilities: {
        inspect_assignment: true,
        mutate_resource: false,
        execute_resource: false,
        browser_ssh: false,
        mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
        safe_mutations: [],
      },
    });
    getWorkspaceResource.mockResolvedValue({
      workspace_id: 'workspace-1',
      resource_type: 'node',
      resource_uuid: '11111111-1111-1111-1111-111111111111',
      effective_permissions: ['remnawave_read', 'remnawave_execute'],
      available_operations: ['inspect_assignment'],
      unavailable_operations: ['mutate_resource', 'execute_resource'],
      forbidden_operations: ['browser_ssh'],
      provider_details_available: false,
      safe_mutations: [],
    });
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findAllByText('resources.types.service_identity')).toHaveLength(2);
    await user.click(screen.getAllByRole('button', { name: 'resources.inspect' })[0]);
    await user.click(await screen.findByRole('button', { name: 'requestSnapshot' }));

    const selector = await screen.findByLabelText('drop.serviceIdentitySelectLabel');
    expect(selector).toHaveValue('');
    expect(screen.getByRole('option', { name: serviceIdentityUuid })).toBeInTheDocument();
    expect(
      screen.queryByRole('option', { name: '33333333-3333-4333-8333-333333333333' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('42')).not.toBeInTheDocument();
    expect(dropNodeConnectionsByServiceIdentity).not.toHaveBeenCalled();
  });
});
