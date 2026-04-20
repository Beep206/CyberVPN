'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import {
  buildPartnerPortalRuntimeState,
  mapWorkspaceProgramsSnapshot,
} from '@/features/partner-portal-state/lib/runtime-state';
import { usePartnerPortalBootstrapState } from '@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state';

function isOptionalPortalAccessError(error: unknown): boolean {
  if (!(error instanceof AxiosError)) {
    return false;
  }
  return error.response?.status === 403 || error.response?.status === 404;
}

async function resolveOptionalPortalResource<T>(loader: () => Promise<{ data: T }>): Promise<T | null> {
  try {
    const response = await loader();
    return response.data;
  } catch (error) {
    if (isOptionalPortalAccessError(error)) {
      return null;
    }
    throw error;
  }
}

export function usePartnerPortalRuntimeState() {
  const bootstrapState = usePartnerPortalBootstrapState();
  const {
    state: baseState,
    bootstrap,
    activeWorkspace,
    workspaceSelection,
    isCanonicalWorkspace,
    queries: {
      bootstrapQuery,
      workspacesQuery,
    },
  } = bootstrapState;

  const workspaceCodesQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-codes', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceCodes(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceCampaignAssetsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-campaign-assets', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceCampaignAssets(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceStatementsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-statements', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceStatements(activeWorkspace.id, {
          limit: 20,
          offset: 0,
        }),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const payoutAccountsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-payout-accounts', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspacePayoutAccounts(activeWorkspace.id, {
          limit: 20,
          offset: 0,
        }),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceConversionRecordsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-conversion-records', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceConversionRecords(activeWorkspace.id, {
          limit: 50,
          offset: 0,
        }),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceAnalyticsMetricsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-analytics-metrics', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceAnalyticsMetrics(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceReportExportsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-report-exports', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceReportExports(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceReviewRequestsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-review-requests', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceReviewRequests(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceCasesQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-cases', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceCases(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceIntegrationCredentialsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-integration-credentials', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceIntegrationCredentials(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceIntegrationDeliveryLogsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-integration-delivery-logs', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceIntegrationDeliveryLogs(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceTrafficDeclarationsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-traffic-declarations', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceTrafficDeclarations(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: false,
  });

  const workspaceNotificationsQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-notifications', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listNotifications({
          workspace_id: activeWorkspace.id,
          include_archived: false,
        }),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 15_000,
    retry: false,
  });

  const notificationPreferencesQuery = useQuery({
    queryKey: ['partner-portal', 'notification-preferences'],
    queryFn: async () => {
      const response = await partnerPortalApi.getNotificationPreferences();
      return response.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  const state = useMemo(
    () => buildPartnerPortalRuntimeState({
      baseState,
      workspace: activeWorkspace ?? null,
      blockedReasons: bootstrap?.blocked_reasons ?? null,
      workspaceCodes: workspaceCodesQuery.data ?? null,
      workspaceCampaignAssets: workspaceCampaignAssetsQuery.data ?? null,
      workspaceStatements: workspaceStatementsQuery.data ?? null,
      workspacePayoutAccounts: payoutAccountsQuery.data ?? null,
      workspaceConversionRecords: workspaceConversionRecordsQuery.data ?? null,
      workspaceAnalyticsMetrics: workspaceAnalyticsMetricsQuery.data ?? null,
      workspaceReportExports: workspaceReportExportsQuery.data ?? null,
      workspaceReviewRequests: workspaceReviewRequestsQuery.data ?? null,
      workspaceTrafficDeclarations: workspaceTrafficDeclarationsQuery.data ?? null,
      workspaceCases: workspaceCasesQuery.data ?? null,
      workspaceNotifications: workspaceNotificationsQuery.data ?? null,
      workspaceIntegrationCredentials: workspaceIntegrationCredentialsQuery.data ?? null,
      workspaceIntegrationDeliveryLogs: workspaceIntegrationDeliveryLogsQuery.data ?? null,
    }),
    [
      activeWorkspace,
      baseState,
      bootstrap?.blocked_reasons,
      payoutAccountsQuery.data,
      workspaceAnalyticsMetricsQuery.data,
      workspaceCasesQuery.data,
      workspaceCampaignAssetsQuery.data,
      workspaceCodesQuery.data,
      workspaceConversionRecordsQuery.data,
      workspaceIntegrationCredentialsQuery.data,
      workspaceIntegrationDeliveryLogsQuery.data,
      workspaceReportExportsQuery.data,
      workspaceReviewRequestsQuery.data,
      workspaceTrafficDeclarationsQuery.data,
      workspaceStatementsQuery.data,
      workspaceNotificationsQuery.data,
    ],
  );

  return {
    state,
    programsSnapshot: mapWorkspaceProgramsSnapshot(
      bootstrap?.programs ?? null,
    ),
    isCanonicalWorkspace,
    activeWorkspace: activeWorkspace ?? null,
    workspaceSelection,
    notificationPreferences: notificationPreferencesQuery.data ?? null,
    isSimulationEnabled: bootstrapState.isSimulationEnabled,
    counters: bootstrap?.counters ?? null,
    pendingTasks: bootstrap?.pending_tasks ?? [],
    blockedReasons: bootstrap?.blocked_reasons ?? [],
    queries: {
      bootstrapQuery,
      workspacesQuery,
      workspaceCodesQuery,
      workspaceCampaignAssetsQuery,
      workspaceStatementsQuery,
      payoutAccountsQuery,
      workspaceConversionRecordsQuery,
      workspaceAnalyticsMetricsQuery,
      workspaceReportExportsQuery,
      workspaceReviewRequestsQuery,
      workspaceIntegrationCredentialsQuery,
      workspaceIntegrationDeliveryLogsQuery,
      workspaceTrafficDeclarationsQuery,
      workspaceCasesQuery,
      workspaceNotificationsQuery,
      notificationPreferencesQuery,
    },
  };
}
