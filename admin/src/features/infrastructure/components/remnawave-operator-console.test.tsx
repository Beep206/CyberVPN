import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AdminRemnawaveCapabilitiesAndStreams } from '@/lib/api/remnawave-status';
import { useAuthStore } from '@/stores/auth-store';

const api = vi.hoisted(() => ({
  getCapabilitiesAndStreams: vi.fn(),
  getTags: vi.fn(),
  setTags: vi.fn(),
  startGeoCheck: vi.fn(),
  getGeoCheck: vi.fn(),
  listNodeIntegrations: vi.fn(),
  createNodeIntegration: vi.fn(),
  updateNodeIntegration: vi.fn(),
  deleteNodeIntegration: vi.fn(),
  listSharedLists: vi.fn(),
  getSharedList: vi.fn(),
  createSharedList: vi.fn(),
  updateSharedList: vi.fn(),
  deleteSharedList: vi.fn(),
  syncSharedList: vi.fn(),
  listRootSnippets: vi.fn(),
  createRootSnippet: vi.fn(),
  updateRootSnippet: vi.fn(),
  deleteRootSnippet: vi.fn(),
  syncRootSnippet: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, values?: Record<string, string | number>) =>
    values ? `${key}:${Object.values(values).join(':')}` : key,
}));

vi.mock('@/lib/api/remnawave-status', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-status')>();
  return {
    ...actual,
    adminRemnawaveStatusApi: { getCapabilitiesAndStreams: api.getCapabilitiesAndStreams },
  };
});

vi.mock('@/lib/api/remnawave-operator', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-operator')>();
  return {
    ...actual,
    remnawaveOperatorApi: {
      getTags: api.getTags,
      setTags: api.setTags,
      startGeoCheck: api.startGeoCheck,
      getGeoCheck: api.getGeoCheck,
      listNodeIntegrations: api.listNodeIntegrations,
      createNodeIntegration: api.createNodeIntegration,
      updateNodeIntegration: api.updateNodeIntegration,
      deleteNodeIntegration: api.deleteNodeIntegration,
      listSharedLists: api.listSharedLists,
      getSharedList: api.getSharedList,
      createSharedList: api.createSharedList,
      updateSharedList: api.updateSharedList,
      deleteSharedList: api.deleteSharedList,
      syncSharedList: api.syncSharedList,
      listRootSnippets: api.listRootSnippets,
      createRootSnippet: api.createRootSnippet,
      updateRootSnippet: api.updateRootSnippet,
      deleteRootSnippet: api.deleteRootSnippet,
      syncRootSnippet: api.syncRootSnippet,
    },
  };
});

import {
  GEO_CHECK_MAX_POLL_ATTEMPTS,
  RemnawaveOperatorConsole,
} from './remnawave-operator-console';

const UUID = '550e8400-e29b-41d4-a716-446655440000';
const CAPABILITIES: AdminRemnawaveCapabilitiesAndStreams = {
  panel_version: '3.4.3',
  target_panel_version: '3.4.3',
  target_node_version: '3.4.1',
  contract_version: '3.4.13',
  capabilities: {
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
  },
  streams: [],
  degraded_reason: null,
};

function setRole(role: 'super_admin' | 'viewer' | 'finance' | 'operator') {
  useAuthStore.setState({
    user: {
      id: UUID,
      email: 'admin@example.com',
      login: 'admin',
      role,
      is_active: true,
      is_email_verified: true,
      created_at: '2026-09-01T00:00:00Z',
    },
    isAuthenticated: true,
  });
}

function renderConsole(initialSection?: Parameters<typeof RemnawaveOperatorConsole>[0]['initialSection']) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return {
    queryClient,
    ...render(<QueryClientProvider client={queryClient}><RemnawaveOperatorConsole initialSection={initialSection} /></QueryClientProvider>),
  };
}

describe('RemnawaveOperatorConsole', () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    setRole('super_admin');
    api.getCapabilitiesAndStreams.mockResolvedValue({ data: CAPABILITIES });
    api.getTags.mockResolvedValue({ data: { resource: 'nodes', tags: ['EDGE_RU'] } });
    api.listNodeIntegrations.mockResolvedValue({ data: { total: 1, items: [{ uuid: UUID, name: 'metrics', description: 'Node metrics', config: { token: 'top-secret-token' } }] } });
    api.listSharedLists.mockResolvedValue({ data: { total: 0, items: [] } });
    api.listRootSnippets.mockResolvedValue({ data: { total: 0, items: [] } });
  });

  it('does not request protected operator data for a role without infrastructure access', () => {
    setRole('finance');
    renderConsole();

    expect(screen.getByRole('alert')).toHaveTextContent('accessDeniedTitle');
    expect(api.getCapabilitiesAndStreams).not.toHaveBeenCalled();
    expect(api.getTags).not.toHaveBeenCalled();
  });

  it('keeps a 202 tag mutation in reconciliation and does not report success', async () => {
    api.getTags.mockResolvedValue({ data: { resource: 'config-profiles', tags: [] } });
    api.setTags.mockResolvedValue({
      kind: 'reconciliation',
      receipt: { attempt_id: UUID, state: 'reconciliation_required', resource_kind: 'tags', requires_reconciliation: true },
    });
    const user = userEvent.setup();
    renderConsole();

    await user.selectOptions(await screen.findByLabelText('resource'), 'config-profiles');
    await user.type(screen.getByLabelText('uuid'), UUID);
    await user.type(screen.getByLabelText('values'), 'EDGE_RU');
    await user.click(screen.getByRole('button', { name: 'save' }));

    expect(await screen.findByText('feedback.reconciliation')).toBeInTheDocument();
    expect(screen.getByText(`feedback.receipt:${UUID}`)).toBeInTheDocument();
    expect(screen.queryByText('saved')).not.toBeInTheDocument();
    expect(api.setTags).toHaveBeenCalledTimes(1);
    expect(api.setTags.mock.calls[0]?.[2]).toMatch(UUID_PATTERN_FOR_TEST);
  });

  it('does not render integration config until an administrator explicitly opens edit', async () => {
    const user = userEvent.setup();
    const { queryClient } = renderConsole();

    await user.click(await screen.findByRole('tab', { name: 'sections.integrations' }));
    expect(await screen.findByText('metrics')).toBeInTheDocument();
    expect(screen.queryByDisplayValue(/top-secret-token/)).not.toBeInTheDocument();
    expect(screen.queryByText(/top-secret-token/)).not.toBeInTheDocument();
    expect(JSON.stringify(queryClient.getQueryData([
      'infrastructure',
      'remnawave-operator',
      'node-integrations',
    ]))).not.toContain('top-secret-token');

    await user.click(screen.getByRole('button', { name: `editNamed:metrics` }));

    expect(screen.getByDisplayValue(/top-secret-token/)).toBeInTheDocument();
    expect(JSON.stringify(queryClient.getMutationCache().getAll().map((entry) => entry.state)))
      .not.toContain('top-secret-token');
  });

  it('mirrors the backend minimum-admin role boundary before loading integration secrets', () => {
    setRole('operator');
    renderConsole();

    expect(screen.getByRole('alert')).toHaveTextContent('accessDeniedTitle');
    expect(screen.queryByDisplayValue(/top-secret-token/)).not.toBeInTheDocument();
    expect(api.getCapabilitiesAndStreams).not.toHaveBeenCalled();
    expect(api.listNodeIntegrations).not.toHaveBeenCalled();
    expect(api.updateNodeIntegration).not.toHaveBeenCalled();
  });

  it('does not mount a disabled capability or issue its data request', async () => {
    api.getCapabilitiesAndStreams.mockResolvedValue({
      data: { ...CAPABILITIES, capabilities: { ...CAPABILITIES.capabilities, node_integrations: false } },
    });
    renderConsole();

    const tab = await screen.findByRole('tab', { name: 'sections.integrations' });
    expect(tab).toBeDisabled();
    expect(api.listNodeIntegrations).not.toHaveBeenCalled();
  });

  it('opens the root-snippets operator directly for migrated legacy bookmarks', async () => {
    renderConsole('snippets');

    expect(await screen.findByRole('tab', { name: 'sections.snippets' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await waitFor(() => expect(api.listRootSnippets).toHaveBeenCalledOnce());
    expect(api.getTags).not.toHaveBeenCalled();
  });

  it('queues one GeoCheck and polls the returned job without replaying the mutation', async () => {
    api.startGeoCheck.mockResolvedValue({ kind: 'committed', resource: { jobId: 'geo-job-1' } });
    api.getGeoCheck.mockResolvedValue({
      data: {
        isCompleted: true,
        isFailed: false,
        result: { success: true, nodeUuid: UUID, image: null, rawReport: { country: 'RU' }, message: 'ok' },
      },
    });
    const user = userEvent.setup();
    renderConsole();

    await user.click(await screen.findByRole('tab', { name: 'sections.geoCheck' }));
    await user.type(screen.getByLabelText('nodeUuid'), UUID);
    await user.click(screen.getByRole('button', { name: 'run' }));

    expect(await screen.findByText('job:geo-job-1')).toBeInTheDocument();
    expect(await screen.findByText('ok')).toBeInTheDocument();
    expect(api.startGeoCheck).toHaveBeenCalledTimes(1);
    expect(api.startGeoCheck.mock.calls[0]?.[0]).toBe(UUID);
    expect(api.startGeoCheck.mock.calls[0]?.[1]).toEqual({});
    expect(api.startGeoCheck.mock.calls[0]?.[2]).toMatch(UUID_PATTERN_FOR_TEST);
    expect(api.getGeoCheck).toHaveBeenCalledWith('geo-job-1');
  });

  it('stops automatic GeoCheck reads at the bounded limit without replaying the job', async () => {
    vi.useFakeTimers();
    try {
      api.startGeoCheck.mockResolvedValue({ kind: 'committed', resource: { jobId: 'geo-job-pending' } });
      api.getGeoCheck.mockResolvedValue({
        data: { isCompleted: false, isFailed: false, result: null },
      });
      renderConsole();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      fireEvent.click(screen.getByRole('tab', { name: 'sections.geoCheck' }));
      fireEvent.change(screen.getByLabelText('nodeUuid'), { target: { value: UUID } });
      fireEvent.click(screen.getByRole('button', { name: 'run' }));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      for (let attempt = 1; attempt < GEO_CHECK_MAX_POLL_ATTEMPTS; attempt += 1) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(2_000);
        });
      }

      expect(api.startGeoCheck).toHaveBeenCalledTimes(1);
      expect(api.getGeoCheck).toHaveBeenCalledTimes(GEO_CHECK_MAX_POLL_ATTEMPTS);
      expect(screen.getByText('pollLimitReached')).toBeInTheDocument();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(20_000);
      });
      expect(api.getGeoCheck).toHaveBeenCalledTimes(GEO_CHECK_MAX_POLL_ATTEMPTS);
    } finally {
      vi.useRealTimers();
    }
  });

  it('renders accepted background sync as pending, not as a committed shared-list update', async () => {
    api.listSharedLists.mockResolvedValue({ data: { total: 1, items: [{ name: 'routing/ru', type: 'cidr', itemsCount: 2 }] } });
    api.syncSharedList.mockResolvedValue({
      kind: 'reconciliation',
      receipt: { attempt_id: UUID, state: 'accepted', resource_kind: 'shared-list', requires_reconciliation: false },
    });
    const user = userEvent.setup();
    renderConsole();

    await user.click(await screen.findByRole('tab', { name: 'sections.sharedLists' }));
    await user.click(await screen.findByRole('button', { name: 'syncNamed:routing/ru' }));

    expect(await screen.findByText('feedback.accepted')).toBeInTheDocument();
    expect(screen.queryByText('updated')).not.toBeInTheDocument();
    expect(api.syncSharedList).toHaveBeenCalledTimes(1);
    expect(api.syncSharedList.mock.calls[0]?.[1]).toMatch(UUID_PATTERN_FOR_TEST);
  });

  it('validates and creates an exact root-snippet JSON array with one idempotency key', async () => {
    api.createRootSnippet.mockResolvedValue({
      kind: 'committed',
      resource: { name: 'headers', snippet: [{ name: 'x-test', value: '1' }] },
    });
    const user = userEvent.setup();
    renderConsole();

    await user.click(await screen.findByRole('tab', { name: 'sections.snippets' }));
    await user.type(screen.getByLabelText('name'), 'headers');
    const value = screen.getByLabelText('value');
    fireEvent.change(value, { target: { value: JSON.stringify([{ name: 'x-test', value: '1' }]) } });
    await user.click(screen.getByRole('button', { name: 'create' }));

    await waitFor(() => expect(api.createRootSnippet).toHaveBeenCalledTimes(1));
    expect(api.createRootSnippet.mock.calls[0]?.[0]).toEqual({
      name: 'headers',
      snippet: [{ name: 'x-test', value: '1' }],
    });
    expect(api.createRootSnippet.mock.calls[0]?.[1]).toMatch(UUID_PATTERN_FOR_TEST);
  });

  it('recovers from a capability-load error only after an explicit read retry', async () => {
    api.getCapabilitiesAndStreams.mockRejectedValueOnce(new Error('temporary')).mockResolvedValueOnce({ data: CAPABILITIES });
    const user = userEvent.setup();
    renderConsole();

    await user.click(await screen.findByRole('button', { name: 'actions.retry' }));

    await waitFor(() => expect(api.getCapabilitiesAndStreams).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole('tab', { name: 'sections.tags' })).toBeEnabled();
  });
});

const UUID_PATTERN_FOR_TEST = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
