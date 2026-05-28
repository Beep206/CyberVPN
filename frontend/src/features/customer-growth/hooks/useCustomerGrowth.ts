import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  codesApi,
  giftsApi,
  growthNotificationsApi,
  invitesApi,
  plansApi,
  referralApi,
} from '@/lib/api';
import type { ResolveGrowthCodeResponse } from '@/lib/api/codes';
import type {
  GiftCodeRecord,
  GiftPurchaseCommitResponse,
  GiftPurchaseRequest,
  GiftRedeemResponse,
} from '@/lib/api/gifts';
import type {
  GrowthNotificationCounters,
  GrowthNotificationDetail,
  GrowthNotificationItem,
  GrowthNotificationPreferences,
} from '@/lib/api/growth-notifications';
import { getGrowthCodeResolutionMessage } from '@/features/customer-growth/lib/checkout-code-resolution';
import {
  areGiftCodesEnabled,
  areInviteCodesEnabled,
  isAnyGrowthSurfaceEnabled,
  isClientCapabilitiesReady,
  isReferralProgramEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';

function pollingInterval(intervalMs: number) {
  if (
    typeof document !== 'undefined' &&
    document.visibilityState === 'hidden'
  ) {
    return false;
  }

  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return false;
  }

  return intervalMs;
}

export function useReferralStatus() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'referral', 'status'],
    enabled: capabilitiesReady && isReferralProgramEnabled(capabilities),
    queryFn: async () => {
      const response = await referralApi.getStatus();
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useReferralCode() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'referral', 'code'],
    enabled: capabilitiesReady && isReferralProgramEnabled(capabilities),
    queryFn: async () => {
      const response = await referralApi.getCode();
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
}

export function useReferralStats() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'referral', 'stats'],
    enabled: capabilitiesReady && isReferralProgramEnabled(capabilities),
    queryFn: async () => {
      const response = await referralApi.getStats();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: () => pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
  });
}

export function useRecentReferralActivity() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'referral', 'activity'],
    enabled: capabilitiesReady && isReferralProgramEnabled(capabilities),
    queryFn: async () => {
      const response = await referralApi.getRecentCommissions();
      return response.data;
    },
    staleTime: 30 * 1000,
  });
}

export const useRecentCommissions = useRecentReferralActivity;

export function useInviteCodes() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'invites'],
    enabled: capabilitiesReady && areInviteCodesEnabled(capabilities),
    queryFn: async () => {
      const response = await invitesApi.getMyInvites();
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useGiftCodes() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'gifts'],
    enabled: capabilitiesReady && areGiftCodesEnabled(capabilities),
    queryFn: async () => {
      const response = await giftsApi.listMyGifts();
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useGiftCatalogPlans() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'gift-plans'],
    enabled: capabilitiesReady && areGiftCodesEnabled(capabilities),
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data.filter((plan) => plan.is_active);
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useGrowthNotifications(includeArchived = false) {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: [
      'growth',
      'notifications',
      includeArchived ? 'archived' : 'active',
    ],
    enabled: capabilitiesReady && isAnyGrowthSurfaceEnabled(capabilities),
    queryFn: async () => {
      const response = await growthNotificationsApi.list(includeArchived);
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: () => pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
  });
}

export function useGrowthNotificationDetail(notificationId: string | null) {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'notifications', 'detail', notificationId],
    enabled:
      capabilitiesReady &&
      isAnyGrowthSurfaceEnabled(capabilities) &&
      Boolean(notificationId),
    queryFn: async () => {
      if (!notificationId) {
        throw new Error('notification_detail_requires_id');
      }
      const response = await growthNotificationsApi.getDetail(notificationId);
      return response.data;
    },
    staleTime: 15 * 1000,
  });
}

export function useGrowthNotificationCounters() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'notifications', 'counters'],
    enabled: capabilitiesReady && isAnyGrowthSurfaceEnabled(capabilities),
    queryFn: async () => {
      const response = await growthNotificationsApi.getCounters();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: () => pollingInterval(30 * 1000),
    refetchIntervalInBackground: false,
  });
}

export function useGrowthNotificationPreferences() {
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useQuery({
    queryKey: ['growth', 'notifications', 'preferences'],
    enabled: capabilitiesReady && isAnyGrowthSurfaceEnabled(capabilities),
    queryFn: async () => {
      const response = await growthNotificationsApi.getPreferences();
      return response.data;
    },
    staleTime: 60 * 1000,
  });
}

export function useMarkGrowthNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['growth', 'notifications', 'read'],
    mutationFn: async (notificationId: string) => {
      const response = await growthNotificationsApi.markRead(notificationId);
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
      ]);
    },
  });
}

export function useArchiveGrowthNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['growth', 'notifications', 'archive'],
    mutationFn: async (notificationId: string) => {
      const response = await growthNotificationsApi.archive(notificationId);
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
      ]);
    },
  });
}

export function useUpdateGrowthNotificationPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['growth', 'notifications', 'preferences', 'update'],
    mutationFn: async (payload: Partial<GrowthNotificationPreferences>) => {
      const response = await growthNotificationsApi.updatePreferences(payload);
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'preferences'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
      ]);
    },
  });
}

export function useRequestGrowthNotificationRecovery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['growth', 'notifications', 'recovery'],
    mutationFn: async ({
      notificationId,
      deliveryChannel,
    }: {
      notificationId: string;
      deliveryChannel: string;
    }) => {
      const response = await growthNotificationsApi.requestRecovery(
        notificationId,
        {
          delivery_channel: deliveryChannel,
        },
      );
      return response.data;
    },
    onSuccess: async (_data, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            'growth',
            'notifications',
            'detail',
            variables.notificationId,
          ],
        }),
      ]);
    },
  });
}

export function useRequestGrowthNotificationSupportEscalation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['growth', 'notifications', 'support-escalation'],
    mutationFn: async ({
      notificationId,
      deliveryChannel,
      escalationChannel,
    }: {
      notificationId: string;
      deliveryChannel?: string | null;
      escalationChannel: string;
    }) => {
      const response = await growthNotificationsApi.requestSupportEscalation(
        notificationId,
        {
          delivery_channel: deliveryChannel ?? null,
          escalation_channel: escalationChannel,
        },
      );
      return response.data;
    },
    onSuccess: async (_data, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            'growth',
            'notifications',
            'detail',
            variables.notificationId,
          ],
        }),
      ]);
    },
  });
}

class GrowthRedeemResolutionError extends Error {
  resolution: ResolveGrowthCodeResponse;

  constructor(resolution: ResolveGrowthCodeResponse) {
    super(getGrowthCodeResolutionMessage(resolution));
    this.name = 'GrowthRedeemResolutionError';
    this.resolution = resolution;
  }
}

function isGrowthRedeemResolutionError(
  error: unknown,
): error is GrowthRedeemResolutionError {
  return error instanceof GrowthRedeemResolutionError;
}

export function getInviteRedeemErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) {
    return 'An error occurred. Please try again.';
  }

  const detail =
    typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail
      : null;

  switch (error.response?.status) {
    case 404:
      return 'Invite code not found or no longer available.';
    case 409:
      return 'Invite code already used.';
    case 410:
      return 'Invite code expired.';
    case 400:
      return detail || 'Invite code is not valid for this account.';
    default:
      return detail || 'Failed to redeem invite code.';
  }
}

export function getGiftRedeemErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) {
    return 'An error occurred. Please try again.';
  }

  const detail =
    typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail
      : null;

  switch (error.response?.status) {
    case 404:
      return 'Gift code not found or no longer available.';
    case 409:
      return 'Gift code has already been redeemed.';
    case 410:
      return 'Gift code expired.';
    case 400:
      return detail || 'Gift code cannot be redeemed for this account.';
    default:
      return detail || 'Failed to redeem gift code.';
  }
}

export function getGrowthRedeemErrorMessage(error: unknown): string {
  if (isGrowthRedeemResolutionError(error)) {
    return getGrowthCodeResolutionMessage(error.resolution);
  }

  if (error instanceof AxiosError) {
    const detail =
      typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : null;

    if (detail?.toLowerCase().includes('gift')) {
      return getGiftRedeemErrorMessage(error);
    }

    return getInviteRedeemErrorMessage(error);
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Failed to redeem code.';
}

export function getGrowthNotificationRecoveryErrorMessage(
  error: unknown,
): string {
  if (!(error instanceof AxiosError)) {
    return 'Failed to request another delivery attempt.';
  }

  const detail =
    typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail
      : null;

  return detail || 'Failed to request another delivery attempt.';
}

export function getGrowthNotificationSupportEscalationErrorMessage(
  error: unknown,
): string {
  if (!(error instanceof AxiosError)) {
    return 'Failed to open guided support escalation.';
  }

  const detail =
    typeof error.response?.data?.detail === 'string'
      ? error.response.data.detail
      : null;

  return detail || 'Failed to open guided support escalation.';
}

export function useRedeemInviteCode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['growth', 'invites', 'redeem'],
    mutationFn: async (code: string) => {
      const response = await invitesApi.redeem({ code });
      return response.data;
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'invites'] }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'referral', 'stats'],
        }),
      ]);
    },
  });
}

export interface GrowthRedeemInviteResult {
  codeType: 'invite';
  inviteCode: Awaited<ReturnType<typeof invitesApi.redeem>>['data'];
}

export interface GrowthRedeemGiftResult {
  codeType: 'gift';
  giftRedemption: GiftRedeemResponse;
}

export type GrowthRedeemResult =
  | GrowthRedeemInviteResult
  | GrowthRedeemGiftResult;

export function useRedeemGrowthCode() {
  const queryClient = useQueryClient();
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useMutation({
    mutationKey: ['growth', 'redeem'],
    mutationFn: async (rawCode: string): Promise<GrowthRedeemResult> => {
      if (
        !capabilitiesReady ||
        (!areInviteCodesEnabled(capabilities) && !areGiftCodesEnabled(capabilities))
      ) {
        throw new Error('Code redemption is not currently available.');
      }

      const normalizedCode = rawCode.trim().toUpperCase();
      const resolutionResponse = await codesApi.resolve({
        code: normalizedCode,
        action_context: 'redeem',
        channel: 'web',
      });
      const resolution = resolutionResponse.data;

      if (!resolution.accepted || !resolution.code_type) {
        throw new GrowthRedeemResolutionError(resolution);
      }

      if (resolution.code_type === 'invite') {
        if (!areInviteCodesEnabled(capabilities)) {
          throw new Error('Invite code flows are not currently available.');
        }

        const response = await invitesApi.redeem({ code: normalizedCode });
        return {
          codeType: 'invite',
          inviteCode: response.data,
        };
      }

      if (resolution.code_type === 'gift') {
        if (!areGiftCodesEnabled(capabilities)) {
          throw new Error('Gift code flows are not currently available.');
        }

        const response = await giftsApi.redeem({ code: normalizedCode });
        return {
          codeType: 'gift',
          giftRedemption: response.data,
        };
      }

      throw new GrowthRedeemResolutionError(
        resolution.accepted
          ? {
              ...resolution,
              accepted: false,
              result: 'rejected',
              reject_reason: 'code_wrong_context',
              wrong_context_target:
                resolution.code_type === 'promo' ||
                resolution.code_type === 'referral'
                  ? 'checkout'
                  : 'redeem',
            }
          : resolution,
      );
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'invites'] }),
        queryClient.invalidateQueries({ queryKey: ['growth', 'gifts'] }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'referral', 'stats'],
        }),
        queryClient.invalidateQueries({ queryKey: ['current-entitlements'] }),
        queryClient.invalidateQueries({ queryKey: ['current-service-state'] }),
        queryClient.invalidateQueries({ queryKey: ['subscriptions'] }),
        queryClient.invalidateQueries({
          queryKey: ['miniapp-current-entitlements'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['miniapp-current-service-state'],
        }),
      ]);
    },
  });
}

export function useGiftPurchase() {
  const queryClient = useQueryClient();
  const capabilitiesQuery = useClientCapabilities();
  const capabilities = capabilitiesQuery.data;
  const capabilitiesReady = isClientCapabilitiesReady(capabilitiesQuery);

  return useMutation({
    mutationKey: ['growth', 'gifts', 'purchase'],
    mutationFn: async (payload: GiftPurchaseRequest) => {
      if (!capabilitiesReady || !areGiftCodesEnabled(capabilities)) {
        throw new Error('Gift purchases are not currently available.');
      }

      const response = await giftsApi.commitPurchase(payload);
      return response.data;
    },
    onSuccess: async (result: GiftPurchaseCommitResponse) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['growth', 'gifts'] }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications'],
        }),
        queryClient.invalidateQueries({
          queryKey: ['growth', 'notifications', 'counters'],
        }),
        queryClient.invalidateQueries({ queryKey: ['payments', 'history'] }),
      ]);

      if (result.gift_code?.id) {
        await queryClient.invalidateQueries({ queryKey: ['growth', 'gifts'] });
      }
    },
  });
}

export type { GiftCodeRecord };
export type {
  GrowthNotificationCounters,
  GrowthNotificationDetail,
  GrowthNotificationItem,
};
