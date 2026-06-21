'use client';

import {
  createContext,
  createElement,
  startTransition,
  useContext,
  useEffect,
  useEffectEvent,
  useMemo,
  type ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { useLocale } from 'next-intl';
import { useProductFeatureFlag } from '@/app/providers/product-intelligence-provider';
import { RateLimitError } from '@/lib/api/client';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import {
  buildPartnerPortalRuntimeState,
  mapWorkspaceProgramsSnapshot,
} from '@/features/partner-portal-state/lib/runtime-state';
import {
  normalizePartnerPortalResourceState,
  normalizePortalResourceError,
} from '@/features/partner-portal-state/lib/resource-state';
import { usePartnerPortalBootstrapState } from '@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state';

const WORKSPACE_QUERY_PREFIXES = [
  ['partner-portal', 'workspace-codes'],
  ['partner-portal', 'workspace-commercial-capabilities'],
  ['partner-portal', 'workspace-finance-summary'],
  ['partner-portal', 'workspace-campaign-assets'],
  ['partner-portal', 'workspace-statements'],
  ['partner-portal', 'workspace-payout-accounts'],
  ['partner-portal', 'workspace-reseller-voucher-batches'],
  ['partner-portal', 'workspace-conversion-records'],
  ['partner-portal', 'workspace-analytics-metrics'],
  ['partner-portal', 'workspace-report-exports'],
  ['partner-portal', 'workspace-review-requests'],
  ['partner-portal', 'workspace-integration-credentials'],
  ['partner-portal', 'workspace-integration-delivery-logs'],
  ['partner-portal', 'workspace-traffic-declarations'],
  ['partner-portal', 'workspace-cases'],
  ['partner-portal', 'workspace-notifications'],
] as const;

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

export function boundedWorkspaceRetry(failureCount: number, error: unknown): boolean {
  const normalizedError = normalizePortalResourceError(error);
  if (
    normalizedError.statusCode === 401
    || normalizedError.statusCode === 403
    || normalizedError.statusCode === 404
  ) {
    return false;
  }

  return failureCount < 2;
}

export function boundedWorkspaceRetryDelay(attemptIndex: number, error: unknown): number {
  if (error instanceof RateLimitError) {
    return Math.min(error.retryAfter * 1000, 120_000);
  }

  return Math.min(1000 * 2 ** attemptIndex, 30_000);
}

type WorkspaceFeedEntry = {
  eventSource: EventSource;
  subscribers: Set<(event: MessageEvent<string>) => void>;
  dispatch: (event: Event) => void;
};

const workspaceFeedEntries = new Map<string, WorkspaceFeedEntry>();

function subscribeWorkspaceFeed(
  workspaceId: string,
  handler: (event: MessageEvent<string>) => void,
): () => void {
  let entry = workspaceFeedEntries.get(workspaceId);
  if (!entry) {
    const eventSource = new EventSource(`/api/v1/partner-workspaces/${workspaceId}/realtime/feed`);
    const subscribers = new Set<(event: MessageEvent<string>) => void>();
    const dispatch = (event: Event) => {
      for (const subscriber of subscribers) {
        subscriber(event as MessageEvent<string>);
      }
    };
    eventSource.addEventListener('partner.workspace.feed', dispatch);
    entry = { eventSource, subscribers, dispatch };
    workspaceFeedEntries.set(workspaceId, entry);
  }
  entry.subscribers.add(handler);
  return () => {
    const current = workspaceFeedEntries.get(workspaceId);
    if (!current) return;
    current.subscribers.delete(handler);
    if (current.subscribers.size === 0) {
      current.eventSource.removeEventListener('partner.workspace.feed', current.dispatch);
      current.eventSource.close();
      workspaceFeedEntries.delete(workspaceId);
    }
  };
}

function usePartnerPortalRuntimeStateValue() {
  const bootstrapState = usePartnerPortalBootstrapState();
  const locale = useLocale();
  const queryClient = useQueryClient();
  const realtimeWorkspaceFeedFlag = useProductFeatureFlag('partner_portal_realtime_workspace_feed_v1');
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

  const invalidateRealtimeWorkspaceSlices = useEffectEvent((workspaceId: string) => {
    startTransition(() => {
      for (const prefix of WORKSPACE_QUERY_PREFIXES) {
        void queryClient.invalidateQueries({ queryKey: [...prefix, workspaceId] });
      }
      void queryClient.invalidateQueries({ queryKey: ['partner-portal', 'session-bootstrap', workspaceId] });
      void queryClient.invalidateQueries({ queryKey: ['partner-portal', 'workspaces'] });
    });
  });

  const handleRealtimeWorkspaceFeedEvent = useEffectEvent((rawEvent: MessageEvent<string>) => {
    try {
      const parsed = JSON.parse(rawEvent.data) as {
        workspace_id?: unknown;
      };
      const workspaceId = typeof parsed.workspace_id === 'string' ? parsed.workspace_id : null;
      if (!workspaceId || workspaceId !== activeWorkspace?.id) {
        return;
      }
      invalidateRealtimeWorkspaceSlices(workspaceId);
    } catch {
      // Ignore malformed realtime events and keep the feed connection alive.
    }
  });

  useEffect(() => {
    if (!activeWorkspace?.id || !realtimeWorkspaceFeedFlag.value) {
      return;
    }

    const eventHandler = (event: MessageEvent<string>) => {
      handleRealtimeWorkspaceFeedEvent(event);
    };
    return subscribeWorkspaceFeed(activeWorkspace.id, eventHandler);
  }, [activeWorkspace?.id, realtimeWorkspaceFeedFlag.value]);

  const workspaceCodesQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-codes', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      const response = await partnerPortalApi.listWorkspaceCodes(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
  });

  const workspaceCommercialCapabilitiesQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-commercial-capabilities', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspaceCommercialCapabilities(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 60_000,
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
  });

  const workspaceFinanceSummaryQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-finance-summary', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspaceFinanceSummary(activeWorkspace.id);
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
  });

  const workspaceResellerVoucherBatchesQuery = useQuery({
    queryKey: ['partner-portal', 'workspace-reseller-voucher-batches', activeWorkspace?.id ?? null],
    queryFn: async () => {
      if (!activeWorkspace) {
        return null;
      }
      return resolveOptionalPortalResource(() =>
        partnerPortalApi.listWorkspaceResellerVoucherBatches(activeWorkspace.id),
      );
    },
    enabled: Boolean(activeWorkspace?.id),
    staleTime: 30_000,
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
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
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
  });

  const notificationPreferencesQuery = useQuery({
    queryKey: ['partner-portal', 'notification-preferences'],
    queryFn: async () => {
      const response = await partnerPortalApi.getNotificationPreferences();
      return response.data;
    },
    staleTime: 60_000,
    retry: boundedWorkspaceRetry,
    retryDelay: boundedWorkspaceRetryDelay,
  });

  const state = useMemo(
    () => buildPartnerPortalRuntimeState({
      baseState,
      workspace: activeWorkspace ?? null,
      locale,
      blockedReasons: bootstrap?.blocked_reasons ?? null,
      workspaceCodes: workspaceCodesQuery.data ?? null,
      workspaceFinanceSummary: workspaceFinanceSummaryQuery.data ?? null,
      workspaceCampaignAssets: workspaceCampaignAssetsQuery.data ?? null,
      workspaceStatements: workspaceStatementsQuery.data ?? null,
      workspacePayoutAccounts: payoutAccountsQuery.data ?? null,
      workspaceResellerVoucherBatches: workspaceResellerVoucherBatchesQuery.data ?? null,
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
      locale,
      payoutAccountsQuery.data,
      workspaceAnalyticsMetricsQuery.data,
      workspaceCasesQuery.data,
      workspaceCampaignAssetsQuery.data,
      workspaceCodesQuery.data,
      workspaceFinanceSummaryQuery.data,
      workspaceConversionRecordsQuery.data,
      workspaceIntegrationCredentialsQuery.data,
      workspaceIntegrationDeliveryLogsQuery.data,
      workspaceResellerVoucherBatchesQuery.data,
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
    resources: {
      workspaceCodes: normalizePartnerPortalResourceState(workspaceCodesQuery, {
        enabled: Boolean(activeWorkspace?.id),
        isEmpty: (codes) => codes.length === 0,
      }),
      workspaceCommercialCapabilities: normalizePartnerPortalResourceState(
        workspaceCommercialCapabilitiesQuery,
        { enabled: Boolean(activeWorkspace?.id) },
      ),
      workspaceFinanceSummary: normalizePartnerPortalResourceState(workspaceFinanceSummaryQuery, {
        enabled: Boolean(activeWorkspace?.id),
      }),
    },
    queries: {
      bootstrapQuery,
      workspacesQuery,
      workspaceCodesQuery,
      workspaceCommercialCapabilitiesQuery,
      workspaceFinanceSummaryQuery,
      workspaceCampaignAssetsQuery,
      workspaceStatementsQuery,
      payoutAccountsQuery,
      workspaceResellerVoucherBatchesQuery,
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

export type PartnerPortalRuntimeStateValue = ReturnType<typeof usePartnerPortalRuntimeStateValue>;

const PartnerPortalRuntimeContext = createContext<PartnerPortalRuntimeStateValue | null>(null);

export function PartnerPortalRuntimeProvider({ children }: { children: ReactNode }) {
  const value = usePartnerPortalRuntimeStateValue();
  return createElement(PartnerPortalRuntimeContext.Provider, { value }, children);
}

export function usePartnerPortalRuntimeState(): PartnerPortalRuntimeStateValue {
  const value = useContext(PartnerPortalRuntimeContext);
  if (!value) {
    throw new Error('usePartnerPortalRuntimeState must be used within PartnerPortalRuntimeProvider');
  }
  return value;
}
