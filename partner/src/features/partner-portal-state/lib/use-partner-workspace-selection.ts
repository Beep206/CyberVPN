'use client';

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  useTransition,
} from 'react';
import { useQuery } from '@tanstack/react-query';
import { usePathname, useRouter } from '@/i18n/navigation';
import { partnerPortalApi, type ListMyPartnerWorkspacesResponse } from '@/lib/api/partner-portal';
import { selectActivePartnerWorkspace } from '@/features/partner-portal-state/lib/runtime-state';

const PARTNER_WORKSPACE_SELECTION_STORAGE_KEY_PREFIX =
  'ozoxy-partner-active-workspace:v1';

function getWorkspaceSelectionStorageKey(host: string): string {
  return `${PARTNER_WORKSPACE_SELECTION_STORAGE_KEY_PREFIX}:${host}`;
}

function readPersistedWorkspaceId(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return window.localStorage.getItem(
    getWorkspaceSelectionStorageKey(window.location.host),
  );
}

function persistWorkspaceId(workspaceId: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(
    getWorkspaceSelectionStorageKey(window.location.host),
    workspaceId,
  );
}

export function buildWorkspaceSelectionQuery(
  searchParams: URLSearchParams | null,
  workspaceId: string,
): Record<string, string> {
  const nextSearchParams = new URLSearchParams(searchParams?.toString() ?? '');
  nextSearchParams.set('workspace', workspaceId);
  return Object.fromEntries(nextSearchParams.entries());
}

function getWorkspaceSelectionSearchSnapshot(): string {
  if (typeof window === 'undefined') {
    return '';
  }

  return window.location.search;
}

function subscribeToWorkspaceSelectionLocation(listener: () => void): () => void {
  if (typeof window === 'undefined') {
    return () => undefined;
  }

  const handleChange = () => listener();
  window.addEventListener('popstate', handleChange);
  window.addEventListener('hashchange', handleChange);

  return () => {
    window.removeEventListener('popstate', handleChange);
    window.removeEventListener('hashchange', handleChange);
  };
}

export interface PartnerWorkspaceSelectionResult {
  workspaces: ListMyPartnerWorkspacesResponse;
  activeWorkspace: ListMyPartnerWorkspacesResponse[number] | null;
  activeWorkspaceId: string | null;
  isSwitching: boolean;
  selectWorkspace: (workspaceId: string) => void;
  workspacesQuery: ReturnType<typeof useQuery<ListMyPartnerWorkspacesResponse>>;
}

export function usePartnerWorkspaceSelection(): PartnerWorkspaceSelectionResult {
  const router = useRouter();
  const pathname = usePathname();
  const locationSearch = useSyncExternalStore(
    subscribeToWorkspaceSelectionLocation,
    getWorkspaceSelectionSearchSnapshot,
    () => '',
  );
  const searchParams = useMemo(
    () => (locationSearch ? new URLSearchParams(locationSearch) : null),
    [locationSearch],
  );
  const queryWorkspaceId = searchParams?.get('workspace') ?? null;
  const persistedWorkspaceId = readPersistedWorkspaceId();
  const [isSwitching, startTransition] = useTransition();
  const [sessionWorkspaceId, setSessionWorkspaceId] = useState<string | null>(
    () => persistedWorkspaceId,
  );

  const workspacesQuery = useQuery({
    queryKey: ['partner-portal', 'workspaces'],
    queryFn: async () => {
      const response = await partnerPortalApi.listMyWorkspaces();
      return response.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  const effectiveWorkspaceId =
    queryWorkspaceId ?? sessionWorkspaceId ?? persistedWorkspaceId;
  const activeWorkspace = useMemo(
    () => selectActivePartnerWorkspace(workspacesQuery.data, effectiveWorkspaceId),
    [effectiveWorkspaceId, workspacesQuery.data],
  );

  useEffect(() => {
    if (!activeWorkspace?.id) {
      return;
    }

    persistWorkspaceId(activeWorkspace.id);
  }, [activeWorkspace?.id]);

  const selectWorkspace = useCallback(
    (workspaceId: string) => {
      if (!workspaceId || workspaceId === activeWorkspace?.id) {
        return;
      }

      persistWorkspaceId(workspaceId);
      setSessionWorkspaceId(workspaceId);

      startTransition(() => {
        router.replace(
          {
            pathname,
            query: buildWorkspaceSelectionQuery(searchParams, workspaceId),
          },
          { scroll: false },
        );
      });
    },
    [activeWorkspace?.id, pathname, router, searchParams],
  );

  return {
    workspaces: workspacesQuery.data ?? [],
    activeWorkspace,
    activeWorkspaceId: activeWorkspace?.id ?? null,
    isSwitching,
    selectWorkspace,
    workspacesQuery,
  };
}
