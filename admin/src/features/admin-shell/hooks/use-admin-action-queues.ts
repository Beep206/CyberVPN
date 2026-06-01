'use client';

import { useQuery } from '@tanstack/react-query';
import { adminWalletApi, governanceApi, growthApi, securityApi, supportApi } from '@/lib/api';
import type {
  AdminNavHref,
  AdminNavItemRisk,
  AdminNavPermissionMode,
} from '@/features/admin-shell/config/admin-navigation';
import { useAuthStore } from '@/stores/auth-store';
import type { AdminPermission, AdminRole } from '@/shared/lib/admin-rbac';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';

type AdminQueueState = 'active' | 'empty' | 'error' | 'loading' | 'unavailable';
type AdminQueueTone = 'danger' | 'muted' | 'success' | 'warning';

interface AdminActionQueueDefinition {
  id: string;
  navItemId: string;
  href: AdminNavHref;
  titleKey: string;
  descriptionKey: string;
  metricKey: string;
  requiredPermissions: readonly AdminPermission[];
  permissionMode?: AdminNavPermissionMode;
  risk: AdminNavItemRisk;
}

interface QueueQueryStatus {
  isError: boolean;
  isPending: boolean;
}

export interface AdminActionQueue extends AdminActionQueueDefinition {
  count: number | null;
  state: AdminQueueState;
  tone: AdminQueueTone;
}

export type AdminQueueBadgeMap = Record<string, number>;

const QUEUE_REFRESH_INTERVAL_MS = 30_000;
const QUEUE_STALE_TIME_MS = 30_000;

const ACTION_QUEUE_DEFINITIONS: readonly AdminActionQueueDefinition[] = [
  {
    id: 'withdrawals',
    navItemId: 'commerce-withdrawals',
    href: '/commerce/withdrawals',
    titleKey: 'actionQueues.withdrawals.title',
    descriptionKey: 'actionQueues.withdrawals.description',
    metricKey: 'actionQueues.withdrawals.metric',
    requiredPermissions: ['payment_read'],
    risk: 'write',
  },
  {
    id: 'support',
    navItemId: 'support',
    href: '/support?status=pending_support',
    titleKey: 'actionQueues.support.title',
    descriptionKey: 'actionQueues.support.description',
    metricKey: 'actionQueues.support.metric',
    requiredPermissions: ['support_ticket_read'],
    risk: 'write',
  },
  {
    id: 'securityReviews',
    navItemId: 'security-review-queue',
    href: '/security/review-queue',
    titleKey: 'actionQueues.securityReviews.title',
    descriptionKey: 'actionQueues.securityReviews.description',
    metricKey: 'actionQueues.securityReviews.metric',
    requiredPermissions: ['audit_read'],
    risk: 'write',
  },
  {
    id: 'growthAbuse',
    navItemId: 'growth-risk',
    href: '/growth/risk',
    titleKey: 'actionQueues.growthAbuse.title',
    descriptionKey: 'actionQueues.growthAbuse.description',
    metricKey: 'actionQueues.growthAbuse.metric',
    requiredPermissions: ['view_analytics', 'manage_invites'],
    permissionMode: 'any',
    risk: 'write',
  },
  {
    id: 'webhookFailures',
    navItemId: 'governance-webhook-log',
    href: '/governance/webhook-log',
    titleKey: 'actionQueues.webhookFailures.title',
    descriptionKey: 'actionQueues.webhookFailures.description',
    metricKey: 'actionQueues.webhookFailures.metric',
    requiredPermissions: ['webhook_read'],
    risk: 'read',
  },
] as const;

function canAccessQueue(
  role: AdminRole | string | null | undefined,
  definition: AdminActionQueueDefinition,
) {
  if (definition.permissionMode === 'any') {
    return definition.requiredPermissions.some((permission) =>
      hasAdminPermission(role, permission),
    );
  }

  return definition.requiredPermissions.every((permission) =>
    hasAdminPermission(role, permission),
  );
}

function pollingInterval(intervalMs: number) {
  return (query: { state: { error: unknown } }) => {
    if (query.state.error) return false;
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return false;
    return intervalMs;
  };
}

function getQueueState(
  canAccess: boolean,
  query: QueueQueryStatus,
  count: number | null,
): AdminQueueState {
  if (!canAccess) return 'unavailable';
  if (query.isPending) return 'loading';
  if (query.isError || count === null) return 'error';
  return count > 0 ? 'active' : 'empty';
}

function getQueueTone(state: AdminQueueState): AdminQueueTone {
  if (state === 'active') return 'warning';
  if (state === 'error') return 'danger';
  if (state === 'empty') return 'success';
  return 'muted';
}

function buildQueue(
  definition: AdminActionQueueDefinition,
  canAccess: boolean,
  query: QueueQueryStatus,
  count: number | null,
): AdminActionQueue {
  const state = getQueueState(canAccess, query, count);

  return {
    ...definition,
    count: state === 'loading' || state === 'unavailable' ? null : count,
    state,
    tone: getQueueTone(state),
  };
}

export function useAdminActionQueues(roleOverride?: AdminRole | string | null) {
  const storeRole = useAuthStore((state) => state.user?.role);
  const role = roleOverride ?? storeRole;
  const canReadWithdrawals = canAccessQueue(role, ACTION_QUEUE_DEFINITIONS[0]);
  const canReadSupport = canAccessQueue(role, ACTION_QUEUE_DEFINITIONS[1]);
  const canReadSecurityReviews = canAccessQueue(role, ACTION_QUEUE_DEFINITIONS[2]);
  const canReadGrowthAbuse = canAccessQueue(role, ACTION_QUEUE_DEFINITIONS[3]);
  const canReadWebhookFailures = canAccessQueue(role, ACTION_QUEUE_DEFINITIONS[4]);

  const withdrawalsQuery = useQuery({
    queryKey: ['admin', 'action-queues', 'withdrawals', 'pending'],
    queryFn: async () => {
      const response = await adminWalletApi.getPendingWithdrawals();
      return response.data.length;
    },
    enabled: canReadWithdrawals,
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: pollingInterval(QUEUE_REFRESH_INTERVAL_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const supportQuery = useQuery({
    queryKey: ['admin', 'action-queues', 'support', 'tickets', { status: 'pending_support', limit: 50 }],
    queryFn: async () => {
      const response = await supportApi.listAdminTickets({
        limit: 50,
        status: 'pending_support',
      });
      return response.data.tickets.length;
    },
    enabled: canReadSupport,
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: pollingInterval(QUEUE_REFRESH_INTERVAL_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const securityReviewsQuery = useQuery({
    queryKey: ['admin', 'action-queues', 'security', 'review-queue'],
    queryFn: async () => {
      const response = await securityApi.listRiskReviewQueue();
      return response.data.length;
    },
    enabled: canReadSecurityReviews,
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: pollingInterval(QUEUE_REFRESH_INTERVAL_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const growthAbuseQuery = useQuery({
    queryKey: ['admin', 'action-queues', 'growth-signals', 'abuse-queue', { limit: 50 }],
    queryFn: async () => {
      const response = await growthApi.listGrowthAbuseSignals({ limit: 50 });
      return response.data.total;
    },
    enabled: canReadGrowthAbuse,
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: pollingInterval(QUEUE_REFRESH_INTERVAL_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const webhookFailuresQuery = useQuery({
    queryKey: ['admin', 'action-queues', 'webhook-log', { page: 1, pageSize: 20, invalidOnly: true }],
    queryFn: async () => {
      const response = await governanceApi.getWebhookLogs({ page: 1, page_size: 20 });
      return response.data.filter((entry) => entry.is_valid === false).length;
    },
    enabled: canReadWebhookFailures,
    staleTime: QUEUE_STALE_TIME_MS,
    refetchInterval: pollingInterval(QUEUE_REFRESH_INTERVAL_MS),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const queues = [
    buildQueue(
      ACTION_QUEUE_DEFINITIONS[0],
      canReadWithdrawals,
      withdrawalsQuery,
      withdrawalsQuery.data ?? null,
    ),
    buildQueue(
      ACTION_QUEUE_DEFINITIONS[1],
      canReadSupport,
      supportQuery,
      supportQuery.data ?? null,
    ),
    buildQueue(
      ACTION_QUEUE_DEFINITIONS[2],
      canReadSecurityReviews,
      securityReviewsQuery,
      securityReviewsQuery.data ?? null,
    ),
    buildQueue(
      ACTION_QUEUE_DEFINITIONS[3],
      canReadGrowthAbuse,
      growthAbuseQuery,
      growthAbuseQuery.data ?? null,
    ),
    buildQueue(
      ACTION_QUEUE_DEFINITIONS[4],
      canReadWebhookFailures,
      webhookFailuresQuery,
      webhookFailuresQuery.data ?? null,
    ),
  ];

  return {
    badges: queues.reduce<AdminQueueBadgeMap>((acc, queue) => {
      if (queue.state === 'active' && queue.count && queue.count > 0) {
        acc[queue.navItemId] = queue.count;
      }

      return acc;
    }, {}),
    queues,
  };
}

export function formatAdminQueueBadge(count: number) {
  return count > 99 ? '99+' : String(count);
}
