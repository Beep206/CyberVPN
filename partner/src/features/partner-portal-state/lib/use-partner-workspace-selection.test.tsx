import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildWorkspaceSelectionQuery,
  usePartnerWorkspaceSelection,
} from './use-partner-workspace-selection';

const mockReplace = vi.fn();
const mockSearchParams = vi.fn(() => new URLSearchParams(''));
const listMyWorkspaces = vi.fn();

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams(),
}));

vi.mock('@/i18n/navigation', () => ({
  usePathname: () => '/dashboard/programs',
  useRouter: () => ({
    replace: mockReplace,
  }),
}));

vi.mock('@/lib/api/partner-portal', () => ({
  partnerPortalApi: {
    listMyWorkspaces: () => listMyWorkspaces(),
  },
}));

const WORKSPACES_FIXTURE = [
  {
    id: 'workspace_001',
    account_key: 'north-star',
    display_name: 'North Star Growth Studio',
    status: 'active',
    legacy_owner_user_id: null,
    created_by_admin_user_id: null,
    code_count: 2,
    active_code_count: 2,
    total_clients: 14,
    total_earned: 240,
    last_activity_at: null,
    current_role_key: 'owner',
    current_permission_keys: ['workspace_read'],
    members: [],
  },
  {
    id: 'workspace_002',
    account_key: 'nebula',
    display_name: 'Nebula Performance Lab',
    status: 'restricted',
    legacy_owner_user_id: null,
    created_by_admin_user_id: null,
    code_count: 1,
    active_code_count: 1,
    total_clients: 6,
    total_earned: 90,
    last_activity_at: null,
    current_role_key: 'manager',
    current_permission_keys: ['workspace_read'],
    members: [],
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('usePartnerWorkspaceSelection', () => {
  beforeEach(() => {
    window.localStorage.clear();
    listMyWorkspaces.mockReset();
    mockReplace.mockReset();
    mockSearchParams.mockReturnValue(new URLSearchParams(''));
    listMyWorkspaces.mockResolvedValue({
      data: WORKSPACES_FIXTURE,
    });
  });

  it('preserves unrelated query params when building the explicit workspace selection query', () => {
    const query = buildWorkspaceSelectionQuery(
      new URLSearchParams('tab=finance&filter=blocked'),
      'workspace_002',
    );

    expect(query).toEqual({
      tab: 'finance',
      filter: 'blocked',
      workspace: 'workspace_002',
    });
  });

  it('hydrates the active workspace from persisted host-scoped selection when no query override exists', async () => {
    window.localStorage.setItem(
      `ozoxy-partner-active-workspace:v1:${window.location.host}`,
      'workspace_002',
    );

    const { result } = renderHook(
      () => usePartnerWorkspaceSelection(),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.activeWorkspaceId).toBe('workspace_002');
    });

    expect(result.current.activeWorkspace?.display_name).toBe(
      'Nebula Performance Lab',
    );
  });

  it('lets the explicit switcher update storage and route state without dropping the current route context', async () => {
    mockSearchParams.mockReturnValue(new URLSearchParams('tab=finance'));

    const { result } = renderHook(
      () => usePartnerWorkspaceSelection(),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.activeWorkspaceId).toBe('workspace_001');
    });

    act(() => {
      result.current.selectWorkspace('workspace_002');
    });

    await waitFor(() => {
      expect(result.current.activeWorkspaceId).toBe('workspace_002');
    });

    expect(mockReplace).toHaveBeenCalledWith(
      {
        pathname: '/dashboard/programs',
        query: {
          tab: 'finance',
          workspace: 'workspace_002',
        },
      },
      { scroll: false },
    );
    expect(
      window.localStorage.getItem(
        `ozoxy-partner-active-workspace:v1:${window.location.host}`,
      ),
    ).toBe('workspace_002');
  });

  it('lets a deep-linked workspace override the persisted host selection', async () => {
    window.localStorage.setItem(
      `ozoxy-partner-active-workspace:v1:${window.location.host}`,
      'workspace_002',
    );
    mockSearchParams.mockReturnValue(
      new URLSearchParams('workspace=workspace_001'),
    );

    const { result } = renderHook(
      () => usePartnerWorkspaceSelection(),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.activeWorkspaceId).toBe('workspace_001');
    });
  });
});
