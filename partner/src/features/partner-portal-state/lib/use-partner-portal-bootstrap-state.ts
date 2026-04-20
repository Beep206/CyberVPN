'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { usePartnerPortalState } from '@/features/partner-portal-state/lib/portal-state';
import { applyPartnerSessionBootstrapToState } from '@/features/partner-portal-state/lib/runtime-state';
import { usePartnerWorkspaceSelection } from '@/features/partner-portal-state/lib/use-partner-workspace-selection';

export function isPartnerPortalSimulationEnabled(): boolean {
  return (
    process.env.NODE_ENV !== 'production'
    && process.env.NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED === 'true'
  );
}

export function usePartnerPortalBootstrapState() {
  const baseState = usePartnerPortalState();
  const workspaceSelection = usePartnerWorkspaceSelection();
  const { activeWorkspace: selectedWorkspace, workspacesQuery } = workspaceSelection;

  const bootstrapQuery = useQuery({
    queryKey: ['partner-portal', 'session-bootstrap', selectedWorkspace?.id ?? null],
    queryFn: async () => {
      const response = await partnerPortalApi.getSessionBootstrap(
        selectedWorkspace?.id ? { workspace_id: selectedWorkspace.id } : undefined,
      );
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });

  const state = useMemo(
    () => applyPartnerSessionBootstrapToState({
      baseState,
      bootstrap: bootstrapQuery.data ?? null,
    }),
    [baseState, bootstrapQuery.data],
  );

  return {
    state,
    bootstrap: bootstrapQuery.data ?? null,
    activeWorkspace: bootstrapQuery.data?.active_workspace ?? selectedWorkspace ?? null,
    workspaces: bootstrapQuery.data?.workspaces ?? workspaceSelection.workspaces,
    activeWorkspaceId: bootstrapQuery.data?.active_workspace_id ?? selectedWorkspace?.id ?? null,
    isCanonicalWorkspace: Boolean(bootstrapQuery.data?.active_workspace?.id),
    isSimulationEnabled: isPartnerPortalSimulationEnabled(),
    workspaceSelection,
    queries: {
      bootstrapQuery,
      workspacesQuery,
    },
  };
}
