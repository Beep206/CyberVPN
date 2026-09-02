import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '@/stores/auth-store';

const { createResourceGrant, listResourceGrants, revokeResourceGrant } = vi.hoisted(() => ({
  createResourceGrant: vi.fn(),
  listResourceGrants: vi.fn(),
  revokeResourceGrant: vi.fn(),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/lib/api/remnawave-status', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/remnawave-status')>();
  return {
    ...actual,
    adminRemnawaveStatusApi: {
      ...actual.adminRemnawaveStatusApi,
      createResourceGrant,
      listResourceGrants,
      revokeResourceGrant,
    },
  };
});

import { RemnawaveGrantsManager } from './remnawave-grants-manager';

const WORKSPACE_ID = '00000000-0000-4000-8000-000000000010';
const RESOURCE_ID = '00000000-0000-4000-8000-000000000020';
const GRANT_ID = '00000000-0000-4000-8000-000000000030';

const activeGrant = {
  id: GRANT_ID,
  workspace_id: WORKSPACE_ID,
  resource_type: 'node' as const,
  resource_uuid: RESOURCE_ID,
  permission_keys: ['remnawave_read'],
  granted_by_admin_user_id: '00000000-0000-4000-8000-000000000001',
  granted_at: '2026-08-30T08:00:00Z',
  revoked_by_admin_user_id: null,
  revoked_at: null,
  audit_reason: 'Approved workspace assignment',
};

function setRole(role: 'super_admin' | 'admin') {
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

function renderManager() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RemnawaveGrantsManager />
    </QueryClientProvider>,
  );
}

describe('RemnawaveGrantsManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setRole('super_admin');
    listResourceGrants.mockResolvedValue({ data: { items: [] } });
    createResourceGrant.mockResolvedValue({ data: activeGrant });
    revokeResourceGrant.mockResolvedValue({
      data: { ...activeGrant, revoked_at: '2026-08-30T09:00:00Z' },
    });
  });

  it('starts with no partner permissions selected and validates before mutation', async () => {
    const user = userEvent.setup();
    renderManager();

    await screen.findByText('empty');
    expect(screen.getByRole('checkbox', { name: 'permissions.remnawave_read' })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'permissions.remnawave_write' })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'permissions.remnawave_execute' })).not.toBeChecked();

    await user.type(screen.getByRole('textbox', { name: 'fields.workspaceId' }), 'invalid');
    await user.type(screen.getByRole('textbox', { name: 'fields.resourceUuid' }), 'invalid');
    await user.click(screen.getByRole('checkbox', { name: 'permissions.remnawave_read' }));
    await user.type(screen.getByRole('textbox', { name: 'fields.reason' }), 'Valid reason');
    await user.click(screen.getByRole('button', { name: 'create.action' }));
    expect(createResourceGrant).not.toHaveBeenCalled();
    expect(screen.getByText('feedback.validation')).toBeInTheDocument();
  });

  it('issues an explicit audited service-identity grant and refreshes authoritative state', async () => {
    const user = userEvent.setup();
    renderManager();
    await screen.findByText('empty');

    await user.type(screen.getByRole('textbox', { name: 'fields.workspaceId' }), WORKSPACE_ID);
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'fields.resourceType' }),
      'service_identity',
    );
    await user.type(screen.getByRole('textbox', { name: 'fields.resourceUuid' }), RESOURCE_ID);
    await user.click(screen.getByRole('checkbox', { name: 'permissions.remnawave_execute' }));
    await user.type(
      screen.getByRole('textbox', { name: 'fields.reason' }),
      'Approved partner service identity execution',
    );
    await user.click(screen.getByRole('button', { name: 'create.action' }));

    await waitFor(() => {
      expect(createResourceGrant).toHaveBeenCalledWith({
        workspace_id: WORKSPACE_ID,
        resource_type: 'service_identity',
        resource_uuid: RESOURCE_ID,
        permission_keys: ['remnawave_execute'],
        reason: 'Approved partner service identity execution',
      });
    });
    expect(await screen.findByText('feedback.created')).toBeInTheDocument();
    expect(listResourceGrants).toHaveBeenCalledTimes(2);
  });

  it('requires a second explicit reason before revoking an active grant', async () => {
    listResourceGrants.mockResolvedValue({ data: { items: [activeGrant] } });
    const user = userEvent.setup();
    renderManager();

    await user.click(await screen.findByRole('button', { name: 'revoke.selectAction' }));
    expect(revokeResourceGrant).not.toHaveBeenCalled();
    const revokeForm = screen.getByText('revoke.title').closest('form');
    expect(revokeForm).not.toBeNull();
    await user.type(
      within(revokeForm!).getByRole('textbox', { name: 'fields.reason' }),
      'Workspace assignment ended',
    );
    await user.click(within(revokeForm!).getByRole('button', { name: 'revoke.confirmAction' }));

    await waitFor(() => {
      expect(revokeResourceGrant).toHaveBeenCalledWith(GRANT_ID, {
        reason: 'Workspace assignment ended',
      });
    });
    expect(await screen.findByText('feedback.revoked')).toBeInTheDocument();
  });

  it('does not request or render grants for roles without manage-admins permission', () => {
    setRole('admin');
    renderManager();

    expect(screen.getByText('permissionDenied')).toBeInTheDocument();
    expect(listResourceGrants).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'create.action' })).not.toBeInTheDocument();
  });

  it('renders a terminal 403 state without a retry mutation', async () => {
    listResourceGrants.mockRejectedValue({ response: { status: 403 } });
    renderManager();

    expect(await screen.findByRole('alert')).toHaveTextContent('permissionDenied');
    expect(screen.queryByRole('button', { name: 'retry' })).not.toBeInTheDocument();
  });
});
