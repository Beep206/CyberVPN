'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Cable,
  CircleAlert,
  CreditCard,
  FileText,
  History,
  KeyRound,
  PencilLine,
  RefreshCw,
  Shield,
  Smartphone,
  Trash2,
  UserRoundPlus,
  Users,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { AxiosError } from 'axios';
import { Link } from '@/i18n/navigation';
import { Button, buttonVariants } from '@/components/ui/button';
import { adminWalletApi } from '@/lib/api/wallet';
import {
  customersApi,
  type AdminCreateCustomerStaffNoteRequest,
  type AdminCustomerPasswordResetRequest,
  type AdminUpdateMobileUserRequest,
} from '@/lib/api/customers';
import { growthApi } from '@/lib/api/growth';
import { paymentsApi } from '@/lib/api/payments';
import { CustomerOperationsInsight } from '@/features/customers/components/customer-operations-insight';
import { CustomersPageShell } from '@/features/customers/components/customers-page-shell';
import { CustomerStatusChip } from '@/features/customers/components/customer-status-chip';
import {
  formatBytes,
  formatCurrencyAmount,
  formatDateTime,
  getErrorMessage,
  humanizeToken,
  shortId,
} from '@/features/customers/lib/formatting';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';

interface CustomerDetailProps {
  userId: string;
}

type StaffNoteCategory = AdminCreateCustomerStaffNoteRequest['category'];
type VpnActionMode = 'enable' | 'disable';
type PlaybookTone = 'danger' | 'warning' | 'info' | 'success';

interface DeviceRevokeCandidate {
  id: string;
  label: string;
  platform: string;
  appVersion: string;
}

interface CustomerPlaybook {
  id: string;
  title: string;
  description: string;
  tone: PlaybookTone;
  actionLabel?: string;
  onAction?: () => void;
}

const NOTE_CATEGORIES: StaffNoteCategory[] = [
  'general',
  'billing',
  'security',
  'support',
];

const PLAYBOOK_TONE_CLASS_MAP: Record<PlaybookTone, string> = {
  danger: 'border-neon-pink/30 bg-neon-pink/10',
  warning: 'border-amber-300/30 bg-amber-300/10',
  info: 'border-neon-cyan/25 bg-neon-cyan/10',
  success: 'border-matrix-green/25 bg-matrix-green/10',
};

function getNoteCategoryTone(category: StaffNoteCategory) {
  if (category === 'billing') {
    return 'warning' as const;
  }
  if (category === 'security') {
    return 'danger' as const;
  }
  if (category === 'support') {
    return 'info' as const;
  }
  return 'neutral' as const;
}

function getTimelineKindTone(kind: string | null | undefined) {
  if (kind === 'payment' || kind === 'wallet_transaction') {
    return 'success' as const;
  }
  if (kind === 'withdrawal') {
    return 'warning' as const;
  }
  if (kind === 'device') {
    return 'info' as const;
  }
  if (kind === 'audit') {
    return 'danger' as const;
  }
  return 'neutral' as const;
}

function getVpnStatusTone(status: string | null | undefined) {
  if (status === 'active') {
    return 'success' as const;
  }
  if (status === 'disabled' || status === 'expired') {
    return 'danger' as const;
  }
  if (status === 'limited') {
    return 'warning' as const;
  }
  return 'neutral' as const;
}

function summarizeTimelineMetadata(metadata: Record<string, unknown> | null | undefined) {
  if (!metadata) {
    return null;
  }

  const summary = Object.entries(metadata)
    .filter(([, value]) =>
      typeof value === 'string'
      || typeof value === 'number'
      || typeof value === 'boolean')
    .slice(0, 3)
    .map(([key, value]) => `${humanizeToken(key)}: ${String(value)}`)
    .join(' • ');

  return summary || null;
}

export function CustomerDetail({ userId }: CustomerDetailProps) {
  const t = useTranslations('Customers');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [statusDraft, setStatusDraft] = useState<string | null>(null);
  const [isActiveDraft, setIsActiveDraft] = useState<boolean | null>(null);
  const [emailDraft, setEmailDraft] = useState<string | null>(null);
  const [usernameDraft, setUsernameDraft] = useState<string | null>(null);
  const [telegramIdDraft, setTelegramIdDraft] = useState<string | null>(null);
  const [telegramUsernameDraft, setTelegramUsernameDraft] = useState<string | null>(null);
  const [referralCodeDraft, setReferralCodeDraft] = useState<string | null>(null);
  const [topupAmount, setTopupAmount] = useState('');
  const [topupDescription, setTopupDescription] = useState('');
  const [noteDraft, setNoteDraft] = useState('');
  const [passwordDraft, setPasswordDraft] = useState('');
  const [recoveryReasonDraft, setRecoveryReasonDraft] = useState('');
  const [revokeDevicesOnPasswordReset, setRevokeDevicesOnPasswordReset] = useState(true);
  const [passwordResetResult, setPasswordResetResult] = useState<{
    password_mode: 'provided' | 'generated';
    device_sessions_cleared: boolean;
    devices_revoked: number;
    generated_password?: string | null;
  } | null>(null);
  const [noteCategory, setNoteCategory] = useState<StaffNoteCategory>('general');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [activationDialogOpen, setActivationDialogOpen] = useState(false);
  const [vpnActionDialog, setVpnActionDialog] = useState<VpnActionMode | null>(null);
  const [deviceToRevoke, setDeviceToRevoke] = useState<DeviceRevokeCandidate | null>(null);
  const [revokeAllDevicesDialogOpen, setRevokeAllDevicesDialogOpen] = useState(false);
  const [subscriptionResyncDialogOpen, setSubscriptionResyncDialogOpen] = useState(false);

  const noteCategoryLabels: Record<StaffNoteCategory, string> = {
    general: t('detail.categories.general'),
    billing: t('detail.categories.billing'),
    security: t('detail.categories.security'),
    support: t('detail.categories.support'),
  };

  const customerQuery = useQuery({
    queryKey: ['customers', 'detail', userId],
    queryFn: async () => {
      const response = await customersApi.getMobileUser(userId);
      return response.data;
    },
    staleTime: 15_000,
  });

  const walletQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'wallet'],
    queryFn: async () => {
      try {
        const response = await adminWalletApi.getWallet(userId);
        return response.data;
      } catch (error) {
        if (error instanceof AxiosError && error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    staleTime: 15_000,
  });

  const paymentsQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'payments'],
    queryFn: async () => {
      const response = await paymentsApi.getHistory({ user_uuid: userId, offset: 0, limit: 20 });
      return response.data;
    },
    staleTime: 15_000,
  });

  const referralQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'referral'],
    queryFn: async () => {
      const response = await growthApi.getReferralUserDetail(userId);
      return response.data;
    },
    staleTime: 15_000,
  });

  const partnerQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'partner'],
    queryFn: async () => {
      const response = await growthApi.getPartnerDetail(userId);
      return response.data;
    },
    enabled: Boolean(customerQuery.data?.is_partner),
    staleTime: 15_000,
  });

  const notesQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'notes'],
    queryFn: async () => {
      const response = await customersApi.listSupportNotes(userId, { offset: 0, limit: 20 });
      return response.data;
    },
    staleTime: 15_000,
  });

  const vpnUserQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'vpn'],
    queryFn: async () => {
      const response = await customersApi.getVpnUser(userId);
      return response.data;
    },
    staleTime: 15_000,
  });

  const subscriptionQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'subscription'],
    queryFn: async () => {
      const response = await customersApi.getSubscriptionSnapshot(userId);
      return response.data;
    },
    staleTime: 15_000,
  });

  const timelineQuery = useQuery({
    queryKey: ['customers', 'detail', userId, 'timeline'],
    queryFn: async () => {
      const response = await customersApi.getTimeline(userId, { limit: 25 });
      return response.data;
    },
    staleTime: 15_000,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { status?: string; is_active?: boolean }) =>
      customersApi.updateMobileUser(userId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'directory'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setStatusDraft(null);
      setIsActiveDraft(null);
      setFeedback(t('detail.statusSaved'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const topupMutation = useMutation({
    mutationFn: () =>
      adminWalletApi.topupWallet(userId, {
        amount: Number(topupAmount || 0),
        description: topupDescription.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'wallet'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setTopupAmount('');
      setTopupDescription('');
      setFeedback(t('detail.topupSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const profileMutation = useMutation({
    mutationFn: (payload: AdminUpdateMobileUserRequest) =>
      customersApi.updateMobileUser(userId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'directory'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setEmailDraft(null);
      setUsernameDraft(null);
      setTelegramIdDraft(null);
      setTelegramUsernameDraft(null);
      setReferralCodeDraft(null);
      setFeedback(t('detail.profileSaved'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const promotePartnerMutation = useMutation({
    mutationFn: () => growthApi.promotePartner({ user_id: userId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'partner'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'directory'] });
      await queryClient.invalidateQueries({ queryKey: ['growth', 'partners'] });
      setFeedback(t('detail.promotePartnerSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const createNoteMutation = useMutation({
    mutationFn: (payload: AdminCreateCustomerStaffNoteRequest) =>
      customersApi.createSupportNote(userId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'notes'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setNoteDraft('');
      setNoteCategory('general');
      setFeedback(t('detail.noteSaved'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const vpnActionMutation = useMutation({
    mutationFn: ({ mode, reason }: { mode: VpnActionMode; reason?: string }) => (
      mode === 'enable'
        ? customersApi.enableVpnUser(userId, { reason: reason ?? null })
        : customersApi.disableVpnUser(userId, { reason: reason ?? null })
    ),
    onSuccess: async (_response, variables) => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'vpn'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'subscription'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setVpnActionDialog(null);
      setFeedback(
        variables.mode === 'enable'
          ? t('detail.vpnEnableSuccess')
          : t('detail.vpnDisableSuccess'),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const revokeDeviceMutation = useMutation({
    mutationFn: (deviceId: string) => customersApi.revokeDevice(userId, deviceId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setDeviceToRevoke(null);
      setFeedback(t('detail.revokeDeviceSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const revokeAllDevicesMutation = useMutation({
    mutationFn: (reason?: string) => customersApi.revokeAllDevices(userId, { reason: reason ?? null }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'directory'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setRevokeAllDevicesDialogOpen(false);
      setFeedback(t('detail.revokeAllDevicesSuccess', { count: response.data.revoked_count }));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (payload: AdminCustomerPasswordResetRequest) =>
      customersApi.resetPassword(userId, payload),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'directory'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setPasswordDraft('');
      setRecoveryReasonDraft('');
      setPasswordResetResult(response.data);
      setFeedback(
        response.data.password_mode === 'generated'
          ? t('detail.passwordResetGeneratedSuccess', { count: response.data.devices_revoked })
          : t('detail.passwordResetSuccess', { count: response.data.devices_revoked }),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const resyncSubscriptionMutation = useMutation({
    mutationFn: (reason?: string) => customersApi.resyncSubscription(userId, { reason: reason ?? null }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'subscription'] });
      await queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] });
      setSubscriptionResyncDialogOpen(false);
      setFeedback(
        response.data.changed
          ? t('detail.subscriptionResyncSuccess')
          : t('detail.subscriptionResyncNoChange'),
      );
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const customer = customerQuery.data;
  const vpnUser = vpnUserQuery.data;
  const subscriptionSnapshot = subscriptionQuery.data;
  const subscriptionLinks = subscriptionSnapshot?.links ?? [];
  const currentStatus = statusDraft ?? customer?.status ?? 'active';
  const currentActive = isActiveDraft ?? customer?.is_active ?? false;
  const hasStateChanges = Boolean(
    customer
    && (currentStatus !== customer.status || currentActive !== customer.is_active),
  );

  if (customerQuery.isLoading) {
    return (
      <CustomersPageShell
        eyebrow={t('detail.eyebrow')}
        title={t('detail.title')}
        description={t('detail.description')}
        icon={Users}
      >
        <div className="h-64 animate-pulse rounded-[1.75rem] border border-grid-line/20 bg-terminal-bg/70" />
      </CustomersPageShell>
    );
  }

  if (customerQuery.isError) {
    return (
      <CustomersPageShell
        eyebrow={t('detail.eyebrow')}
        title={t('detail.title')}
        description={t('detail.description')}
        icon={Users}
      >
        <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
          {getErrorMessage(customerQuery.error, t('detail.loadError'))}
        </div>
      </CustomersPageShell>
    );
  }

  if (!customer) {
    return null;
  }

  const currentEmail = emailDraft ?? customer.email;
  const currentUsername = usernameDraft ?? customer.username ?? '';
  const currentTelegramId = telegramIdDraft ?? (customer.telegram_id ? String(customer.telegram_id) : '');
  const currentTelegramUsername = telegramUsernameDraft ?? customer.telegram_username ?? '';
  const currentReferralCode = referralCodeDraft ?? customer.referral_code ?? '';
  const normalizedEmail = currentEmail.trim().toLowerCase();
  const normalizedUsername = currentUsername.trim() || null;
  const normalizedTelegramId = currentTelegramId.trim();
  const parsedTelegramId = normalizedTelegramId ? Number(normalizedTelegramId) : null;
  const hasValidTelegramId = !normalizedTelegramId || !Number.isNaN(parsedTelegramId);
  const normalizedTelegramUsername = currentTelegramUsername.trim().replace(/^@+/, '') || null;
  const normalizedReferralCode = currentReferralCode.trim().toUpperCase() || null;
  const storedSubscriptionUrl = customer.subscription_url ?? null;
  const upstreamSubscriptionUrl = subscriptionSnapshot?.subscription_url ?? null;
  const subscriptionLinkDrift = Boolean(
    upstreamSubscriptionUrl
    && upstreamSubscriptionUrl !== storedSubscriptionUrl,
  );
  const canResyncSubscription = Boolean(upstreamSubscriptionUrl);
  const shadowsocksLinksCount = Object.keys(subscriptionSnapshot?.ss_conf_links ?? {}).length;
  const hasProfileChanges = (
    normalizedEmail !== customer.email
    || normalizedUsername !== customer.username
    || parsedTelegramId !== customer.telegram_id
    || normalizedTelegramUsername !== customer.telegram_username
    || normalizedReferralCode !== customer.referral_code
  );

  function scrollToSection(sectionId: string) {
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }

  async function handleProfileSave() {
    if (!normalizedEmail) {
      setFeedback(t('detail.invalidEmail'));
      return;
    }

    if (!hasValidTelegramId) {
      setFeedback(t('detail.invalidTelegramId'));
      return;
    }

    await profileMutation.mutateAsync({
      email: normalizedEmail,
      username: normalizedUsername,
      telegram_id: parsedTelegramId,
      telegram_username: normalizedTelegramUsername,
      referral_code: normalizedReferralCode,
    });
  }

  async function handlePasswordReset(mode: 'provided' | 'generated') {
    if (mode === 'provided') {
      if (passwordDraft.trim().length === 0) {
        setFeedback(t('detail.passwordRequired'));
        return;
      }

      await resetPasswordMutation.mutateAsync({
        new_password: passwordDraft.trim(),
        generate_temporary_password: false,
        revoke_all_devices: revokeDevicesOnPasswordReset,
        reason: recoveryReasonDraft.trim() || null,
      });
      return;
    }

    await resetPasswordMutation.mutateAsync({
      generate_temporary_password: true,
      revoke_all_devices: revokeDevicesOnPasswordReset,
      reason: recoveryReasonDraft.trim() || null,
    });
  }

  const playbooks: CustomerPlaybook[] = [];

  if (!customer.is_active) {
    playbooks.push({
      id: 'reactivate-app',
      title: t('detail.playbooks.reactivateAppTitle'),
      description: t('detail.playbooks.reactivateAppDescription'),
      tone: 'danger',
      actionLabel: t('common.reactivate'),
      onAction: () => setActivationDialogOpen(true),
    });
  }

  if (!customer.remnawave_uuid) {
    playbooks.push({
      id: 'missing-vpn-link',
      title: t('detail.playbooks.missingVpnLinkTitle'),
      description: t('detail.playbooks.missingVpnLinkDescription'),
      tone: 'warning',
      actionLabel: t('detail.playbooks.reviewProfile'),
      onAction: () => scrollToSection('customer-identity-section'),
    });
  } else if (vpnUser?.exists && vpnUser.status !== 'active') {
    playbooks.push({
      id: 'restore-vpn',
      title: t('detail.playbooks.restoreVpnTitle'),
      description: t('detail.playbooks.restoreVpnDescription'),
      tone: 'warning',
      actionLabel: t('detail.playbooks.restoreVpnAction'),
      onAction: () => setVpnActionDialog('enable'),
    });
  }

  if (subscriptionSnapshot?.config_error || subscriptionSnapshot?.status === 'expired') {
    playbooks.push({
      id: 'subscription-review',
      title: t('detail.playbooks.subscriptionReviewTitle'),
      description: t('detail.playbooks.subscriptionReviewDescription'),
      tone: 'info',
      actionLabel: t('detail.playbooks.openSubscription'),
      onAction: () => scrollToSection('customer-subscription-section'),
    });
  }

  if (subscriptionLinkDrift) {
    playbooks.push({
      id: 'subscription-link-drift',
      title: t('detail.playbooks.subscriptionLinkDriftTitle'),
      description: t('detail.playbooks.subscriptionLinkDriftDescription'),
      tone: 'warning',
      actionLabel: t('detail.playbooks.resyncSubscriptionAction'),
      onAction: () => setSubscriptionResyncDialogOpen(true),
    });
  }

  if (customer.devices.length > 3) {
    playbooks.push({
      id: 'device-hygiene',
      title: t('detail.playbooks.deviceHygieneTitle'),
      description: t('detail.playbooks.deviceHygieneDescription', {
        count: customer.devices.length,
      }),
      tone: 'info',
      actionLabel: t('detail.playbooks.revokeAllDevicesAction'),
      onAction: () => setRevokeAllDevicesDialogOpen(true),
    });
  }

  if ((notesQuery.data?.length ?? 0) === 0) {
    playbooks.push({
      id: 'add-first-note',
      title: t('detail.playbooks.addFirstNoteTitle'),
      description: t('detail.playbooks.addFirstNoteDescription'),
      tone: 'success',
      actionLabel: t('detail.playbooks.addFirstNoteAction'),
      onAction: () => scrollToSection('customer-notes-section'),
    });
  }

  if (customer.is_active) {
    playbooks.push({
      id: 'credential-recovery',
      title: t('detail.playbooks.credentialRecoveryTitle'),
      description: t('detail.playbooks.credentialRecoveryDescription'),
      tone: customer.devices.length > 0 ? 'warning' : 'info',
      actionLabel: t('detail.playbooks.openRecovery'),
      onAction: () => scrollToSection('customer-recovery-section'),
    });
  }

  const timelineItems = timelineQuery.data?.items ?? [];

  return (
    <CustomersPageShell
      eyebrow={t('detail.eyebrow')}
      title={customer.email}
      description={t('detail.description')}
      icon={Users}
      actions={
        <>
          <Link
            href="/customers"
            className={buttonVariants({ variant: 'ghost' })}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('detail.backToDirectory')}
          </Link>
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              void Promise.all([
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'wallet'] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'payments'] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'notes'] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'vpn'] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'subscription'] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'timeline'] }),
                queryClient.invalidateQueries({ queryKey: ['customers', 'detail', userId, 'operations-insight'] }),
              ]);
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
          {customer.is_partner ? null : (
            <Button
              type="button"
              magnetic={false}
              disabled={promotePartnerMutation.isPending}
              onClick={() => promotePartnerMutation.mutate()}
            >
              <UserRoundPlus className="mr-2 h-4 w-4" />
              {t('detail.promotePartner')}
            </Button>
          )}
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            disabled={updateMutation.isPending || !hasStateChanges}
            onClick={() => {
              void updateMutation.mutateAsync({
                status: currentStatus,
                is_active: currentActive,
              });
            }}
          >
            {t('detail.saveState')}
          </Button>
          <Button
            type="button"
            magnetic={false}
            variant={currentActive ? 'destructive' : 'default'}
            onClick={() => setActivationDialogOpen(true)}
          >
            {currentActive ? t('common.deactivate') : t('common.reactivate')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('detail.metrics.devices'),
          value: String(customer.devices.length),
          hint: t('detail.metrics.devicesHint'),
          tone: 'info',
        },
        {
          label: t('detail.metrics.wallet'),
          value: formatCurrencyAmount(walletQuery.data?.balance, walletQuery.data?.currency ?? 'USD', locale),
          hint: t('detail.metrics.walletHint'),
          tone: 'success',
        },
        {
          label: t('detail.metrics.payments'),
          value: String(paymentsQuery.data?.payments.length ?? 0),
          hint: t('detail.metrics.paymentsHint'),
          tone: 'neutral',
        },
        {
          label: t('detail.metrics.referral'),
          value: formatCurrencyAmount(referralQuery.data?.total_earned, 'USD', locale),
          hint: t('detail.metrics.referralHint'),
          tone: 'warning',
        },
        {
          label: t('detail.metrics.partner'),
          value: formatCurrencyAmount(partnerQuery.data?.total_earned, 'USD', locale),
          hint: t('detail.metrics.partnerHint'),
          tone: customer.is_partner ? 'warning' : 'neutral',
        },
      ]}
    >
      <div className="grid gap-6">
        {feedback ? (
          <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
            {feedback}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-12">
          <section
            id="customer-identity-section"
            className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7"
          >
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('detail.identityTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('detail.identityDescription')}
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {[
                [t('common.customerId'), customer.id],
                [t('common.email'), customer.email],
                [t('common.username'), customer.username ?? '--'],
                [t('common.telegram'), customer.telegram_username ? `@${customer.telegram_username}` : customer.telegram_id ?? '--'],
                [t('common.referralCode'), customer.referral_code ?? '--'],
                [t('common.remnawaveUuid'), customer.remnawave_uuid ?? '--'],
                [t('common.subscriptionUrl'), customer.subscription_url ?? '--'],
                [t('common.createdAt'), formatDateTime(customer.created_at, locale)],
                [t('common.lastLogin'), formatDateTime(customer.last_login_at, locale)],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {label}
                  </p>
                  <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-6 xl:col-span-5">
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('detail.stateTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('detail.stateDescription')}
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                <CustomerStatusChip
                  label={customer.is_active ? t('common.active') : t('common.inactive')}
                  tone={customer.is_active ? 'success' : 'warning'}
                />
                <CustomerStatusChip
                  label={customer.is_partner ? t('common.partner') : t('common.none')}
                  tone={customer.is_partner ? 'warning' : 'neutral'}
                />
              </div>

              <div className="mt-5 grid gap-4">
                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.status')}
                  </span>
                  <input
                    value={currentStatus}
                    onChange={(event) => setStatusDraft(event.target.value)}
                    className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                  />
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.current')}
                  </span>
                  <select
                    value={currentActive ? 'active' : 'inactive'}
                    onChange={(event) => setIsActiveDraft(event.target.value === 'active')}
                    className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                  >
                    <option value="active">{t('common.active')}</option>
                    <option value="inactive">{t('common.inactive')}</option>
                  </select>
                </label>
              </div>
            </article>

            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('detail.walletTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('detail.walletDescription')}
              </p>

              <div className="mt-5 grid gap-3">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.balance')}
                  </p>
                  <p className="mt-2 text-xl font-display tracking-[0.12em] text-white">
                    {walletQuery.data
                      ? formatCurrencyAmount(walletQuery.data.balance, walletQuery.data.currency, locale)
                      : '--'}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.frozen')}
                  </p>
                  <p className="mt-2 text-xl font-display tracking-[0.12em] text-white">
                    {walletQuery.data
                      ? formatCurrencyAmount(walletQuery.data.frozen, walletQuery.data.currency, locale)
                      : '--'}
                  </p>
                </div>
              </div>

              {walletQuery.data === null ? (
                <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-6 text-sm font-mono text-muted-foreground">
                  {t('detail.walletUnavailable')}
                </div>
              ) : (
                <div className="mt-5 grid gap-3">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={topupAmount}
                    onChange={(event) => setTopupAmount(event.target.value)}
                    placeholder={t('detail.topupAmountPlaceholder')}
                    className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                  />
                  <input
                    value={topupDescription}
                    onChange={(event) => setTopupDescription(event.target.value)}
                    placeholder={t('detail.topupDescriptionPlaceholder')}
                    className="h-10 rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                  />
                  <Button
                    type="button"
                    magnetic={false}
                    disabled={topupMutation.isPending || Number(topupAmount || 0) <= 0}
                    onClick={() => {
                      void topupMutation.mutateAsync();
                    }}
                  >
                    <CreditCard className="mr-2 h-4 w-4" />
                    {t('common.topup')}
                  </Button>
                </div>
              )}
            </article>
          </section>
        </div>

        <div className="grid gap-6 xl:grid-cols-12">
          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('detail.profileTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('detail.profileDescription')}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
                <PencilLine className="h-4 w-4" />
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="space-y-2 md:col-span-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.email')}
                </span>
                <input
                  type="email"
                  value={currentEmail}
                  onChange={(event) => setEmailDraft(event.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.username')}
                </span>
                <input
                  value={currentUsername}
                  onChange={(event) => setUsernameDraft(event.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.referralCode')}
                </span>
                <input
                  value={currentReferralCode}
                  onChange={(event) => setReferralCodeDraft(event.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground uppercase"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.telegram')}
                </span>
                <input
                  value={currentTelegramUsername}
                  onChange={(event) => setTelegramUsernameDraft(event.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('detail.labels.telegramId')}
                </span>
                <input
                  value={currentTelegramId}
                  onChange={(event) => setTelegramIdDraft(event.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                />
              </label>
            </div>

            <div className="mt-5 flex justify-end">
              <Button
                type="button"
                magnetic={false}
                disabled={profileMutation.isPending || !hasProfileChanges || !normalizedEmail || !hasValidTelegramId}
                onClick={() => {
                  void handleProfileSave();
                }}
              >
                <PencilLine className="mr-2 h-4 w-4" />
                {t('detail.saveProfile')}
              </Button>
            </div>
          </section>

          <section
            id="customer-subscription-section"
            className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('detail.subscriptionTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('detail.subscriptionDescription')}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  magnetic={false}
                  disabled={resyncSubscriptionMutation.isPending || !canResyncSubscription}
                  onClick={() => setSubscriptionResyncDialogOpen(true)}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {t('detail.resyncSubscription')}
                </Button>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
                  <Cable className="h-4 w-4" />
                </div>
              </div>
            </div>

            {subscriptionQuery.isLoading ? (
              <div className="mt-5 grid gap-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))}
              </div>
            ) : subscriptionQuery.isError ? (
              <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                {getErrorMessage(subscriptionQuery.error, t('detail.subscriptionLoadError'))}
              </div>
            ) : !subscriptionSnapshot?.exists ? (
              <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                {subscriptionSnapshot?.config_error ?? t('detail.subscriptionEmpty')}
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                {subscriptionLinkDrift ? (
                  <div className="rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-sm font-mono text-amber-100">
                    {t('detail.subscriptionLinkDriftWarning')}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <CustomerStatusChip
                    label={humanizeToken(subscriptionSnapshot.status)}
                    tone={getVpnStatusTone(subscriptionSnapshot.status)}
                  />
                  <CustomerStatusChip
                    label={subscriptionSnapshot.config_client_type ?? 'subscription'}
                    tone="info"
                  />
                  {subscriptionSnapshot.days_left !== null && subscriptionSnapshot.days_left !== undefined ? (
                    <CustomerStatusChip
                      label={t('detail.subscriptionDaysLeft', { count: subscriptionSnapshot.days_left })}
                      tone="neutral"
                    />
                  ) : null}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    [t('detail.labels.storedSubscriptionUrl'), storedSubscriptionUrl ?? '--'],
                    [t('detail.labels.upstreamSubscriptionUrl'), upstreamSubscriptionUrl ?? '--'],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </p>
                      <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    [t('common.expiresAt'), formatDateTime(subscriptionSnapshot.expires_at, locale)],
                    [t('detail.labels.onlineAt'), formatDateTime(subscriptionSnapshot.online_at, locale)],
                    [t('detail.labels.deviceLimit'), subscriptionSnapshot.hwid_device_limit ?? '--'],
                    [t('detail.labels.lastTrafficReset'), formatDateTime(subscriptionSnapshot.last_traffic_reset_at, locale)],
                    [t('detail.labels.userAgent'), subscriptionSnapshot.sub_last_user_agent ?? '--'],
                    [t('detail.labels.shortUuid'), subscriptionSnapshot.short_uuid ?? '--'],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </p>
                      <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {[
                    [t('common.used'), formatBytes(subscriptionSnapshot.used_traffic_bytes)],
                    [t('common.limit'), formatBytes(subscriptionSnapshot.traffic_limit_bytes)],
                    [t('detail.labels.download'), formatBytes(subscriptionSnapshot.download_bytes)],
                    [t('detail.labels.upload'), formatBytes(subscriptionSnapshot.upload_bytes)],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </p>
                      <p className="mt-2 text-sm font-display tracking-[0.12em] text-white">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  {[
                    [t('detail.labels.lifetimeTraffic'), formatBytes(subscriptionSnapshot.lifetime_used_traffic_bytes)],
                    [t('detail.labels.subscriptionRevokedAt'), formatDateTime(subscriptionSnapshot.sub_revoked_at, locale)],
                    [t('detail.labels.ssConfigLinks'), String(shadowsocksLinksCount)],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </p>
                      <p className="mt-2 text-sm font-display tracking-[0.12em] text-white">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.subscriptionUrl')}
                  </p>
                  <p className="mt-2 break-all text-sm font-mono text-white">
                    {subscriptionSnapshot.subscription_url ?? '--'}
                  </p>
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.configTitle')}
                      </p>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {subscriptionSnapshot.config_error ?? t('detail.configDescription')}
                      </p>
                    </div>
                    {subscriptionSnapshot.subscription_url ? (
                      <a
                        href={subscriptionSnapshot.subscription_url}
                        target="_blank"
                        rel="noreferrer"
                        className={buttonVariants({ variant: 'ghost' })}
                      >
                        {t('detail.openSubscriptionUrl')}
                      </a>
                    ) : null}
                  </div>
                  <textarea
                    readOnly
                    rows={5}
                    value={subscriptionSnapshot.config ?? ''}
                    className="mt-4 flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('detail.linksTitle')}
                  </p>
                  <div className="mt-3 space-y-2">
                    {subscriptionLinks.length ? subscriptionLinks.slice(0, 3).map((link) => (
                      <p
                        key={link}
                        className="break-all rounded-xl border border-grid-line/20 bg-terminal-bg/60 px-3 py-2 text-xs font-mono text-white"
                      >
                        {link}
                      </p>
                    )) : (
                      <p className="text-sm font-mono text-muted-foreground">
                        {t('detail.linksEmpty')}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('detail.playbooksTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('detail.playbooksDescription')}
              </p>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
              <CircleAlert className="h-4 w-4" />
            </div>
          </div>

          <div className="mt-5 grid gap-3 xl:grid-cols-2">
            {playbooks.length ? playbooks.map((playbook) => (
              <article
                key={playbook.id}
                className={`rounded-2xl border p-4 ${PLAYBOOK_TONE_CLASS_MAP[playbook.tone]}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-2">
                    <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                      {playbook.title}
                    </p>
                    <p className="text-sm font-mono leading-6 text-white/80">
                      {playbook.description}
                    </p>
                  </div>
                  {playbook.actionLabel && playbook.onAction ? (
                    <Button
                      type="button"
                      magnetic={false}
                      size="sm"
                      variant="ghost"
                      onClick={playbook.onAction}
                    >
                      {playbook.actionLabel}
                    </Button>
                  ) : null}
                </div>
              </article>
            )) : (
              <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground xl:col-span-2">
                {t('detail.playbooksEmpty')}
              </div>
            )}
          </div>
        </section>

        <section
          id="customer-recovery-section"
          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('detail.recoveryTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('detail.recoveryDescription')}
              </p>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
              <KeyRound className="h-4 w-4" />
            </div>
          </div>

          <div className="mt-5 grid gap-6 xl:grid-cols-12">
            <div className="space-y-4 xl:col-span-7">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('detail.passwordLabel')}
                </span>
                <input
                  type="password"
                  value={passwordDraft}
                  onChange={(event) => {
                    setPasswordDraft(event.target.value);
                    if (passwordResetResult) {
                      setPasswordResetResult(null);
                    }
                  }}
                  placeholder={t('detail.passwordPlaceholder')}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                />
              </label>

              <p className="text-xs font-mono leading-6 text-muted-foreground">
                {t('detail.passwordRequirements')}
              </p>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('detail.recoveryReasonLabel')}
                </span>
                <textarea
                  rows={4}
                  value={recoveryReasonDraft}
                  onChange={(event) => setRecoveryReasonDraft(event.target.value)}
                  placeholder={t('detail.recoveryReasonPlaceholder')}
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>

              <label className="flex items-start gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                <input
                  type="checkbox"
                  checked={revokeDevicesOnPasswordReset}
                  onChange={(event) => setRevokeDevicesOnPasswordReset(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-input bg-transparent text-neon-cyan"
                />
                <div>
                  <p className="text-sm font-mono text-white">
                    {t('detail.revokeDevicesAfterReset')}
                  </p>
                  <p className="mt-1 text-xs font-mono leading-6 text-muted-foreground">
                    {t('detail.revokeDevicesAfterResetHint', { count: customer.devices.length })}
                  </p>
                </div>
              </label>

              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  magnetic={false}
                  disabled={resetPasswordMutation.isPending || passwordDraft.trim().length === 0}
                  onClick={() => {
                    void handlePasswordReset('provided');
                  }}
                >
                  <KeyRound className="mr-2 h-4 w-4" />
                  {t('detail.setPassword')}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  magnetic={false}
                  disabled={resetPasswordMutation.isPending}
                  onClick={() => {
                    void handlePasswordReset('generated');
                  }}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {t('detail.generateTemporaryPassword')}
                </Button>
              </div>
            </div>

            <div className="space-y-4 xl:col-span-5">
              <div className="rounded-2xl border border-amber-300/30 bg-amber-300/10 p-4">
                <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                  {t('detail.recoveryProtocolTitle')}
                </p>
                <p className="mt-2 text-sm font-mono leading-6 text-amber-100">
                  {t('detail.recoveryProtocolDescription')}
                </p>
              </div>

              {passwordResetResult ? (
                <div className="space-y-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.passwordMode')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {humanizeToken(passwordResetResult.password_mode)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.devicesRevoked')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {String(passwordResetResult.devices_revoked)}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/60 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('detail.labels.deviceSessionsCleared')}
                    </p>
                    <p className="mt-2 text-sm font-mono text-white">
                      {passwordResetResult.device_sessions_cleared
                        ? t('detail.deviceSessionsClearedYes')
                        : t('detail.deviceSessionsClearedNo')}
                    </p>
                  </div>

                  {passwordResetResult.generated_password ? (
                    <div className="rounded-2xl border border-neon-cyan/25 bg-neon-cyan/10 p-4">
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.generatedPassword')}
                      </p>
                      <p className="mt-2 break-all text-sm font-mono text-white">
                        {passwordResetResult.generated_password}
                      </p>
                      <p className="mt-3 text-xs font-mono leading-6 text-muted-foreground">
                        {t('detail.generatedPasswordHint')}
                      </p>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                  {t('detail.recoveryResultEmpty')}
                </div>
              )}
            </div>
          </div>
        </section>

        <CustomerOperationsInsight userId={userId} />

        <div className="grid gap-6 xl:grid-cols-12">
          <section
            id="customer-devices-section"
            className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('detail.devicesTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('detail.devicesDescription')}
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                magnetic={false}
                disabled={revokeAllDevicesMutation.isPending || customer.devices.length === 0}
                onClick={() => setRevokeAllDevicesDialogOpen(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t('detail.revokeAllDevices')}
              </Button>
            </div>

            <div className="mt-5 space-y-3">
              {customer.devices.length ? customer.devices.map((device) => (
                <div
                  key={device.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                        <Smartphone className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {device.device_model}
                        </p>
                        <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {device.platform} / {device.app_version}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <CustomerStatusChip
                        label={shortId(device.device_id, 10)}
                        tone="info"
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        magnetic={false}
                        disabled={revokeDeviceMutation.isPending}
                        onClick={() => {
                          setDeviceToRevoke({
                            id: device.id,
                            label: device.device_model,
                            platform: device.platform,
                            appVersion: device.app_version,
                          });
                        }}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        {t('common.revoke')}
                      </Button>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.lastActive')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {formatDateTime(device.last_active_at, locale)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.platform')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {device.platform} / {device.os_version}
                      </p>
                    </div>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                  {t('detail.devicesEmpty')}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('detail.vpnTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('detail.vpnDescription')}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
                <Shield className="h-4 w-4" />
              </div>
            </div>

            {vpnUserQuery.isLoading ? (
              <div className="mt-5 grid gap-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-20 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))}
              </div>
            ) : vpnUserQuery.isError ? (
              <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                {getErrorMessage(vpnUserQuery.error, t('detail.vpnLoadError'))}
              </div>
            ) : !vpnUser?.exists ? (
              <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                {t('detail.vpnUnavailable')}
              </div>
            ) : (
              <>
                <div className="mt-5 flex flex-wrap gap-2">
                  <CustomerStatusChip
                    label={humanizeToken(vpnUser.status)}
                    tone={getVpnStatusTone(vpnUser.status)}
                  />
                  <CustomerStatusChip
                    label={vpnUser.short_uuid ?? shortId(vpnUser.subscription_uuid, 10)}
                    tone="info"
                  />
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {[
                    [t('common.username'), vpnUser.username ?? '--'],
                    [t('common.email'), vpnUser.email ?? '--'],
                    [t('detail.labels.shortUuid'), vpnUser.short_uuid ?? '--'],
                    [t('common.expiresAt'), formatDateTime(vpnUser.expire_at, locale)],
                    [t('common.createdAt'), formatDateTime(vpnUser.created_at, locale)],
                    [t('common.telegram'), vpnUser.telegram_id ? String(vpnUser.telegram_id) : '--'],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </p>
                      <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.used')}
                    </p>
                    <p className="mt-2 text-xl font-display tracking-[0.12em] text-white">
                      {formatBytes(vpnUser.used_traffic_bytes)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('common.limit')}
                    </p>
                    <p className="mt-2 text-xl font-display tracking-[0.12em] text-white">
                      {formatBytes(vpnUser.traffic_limit_bytes)}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex justify-end">
                  <Button
                    type="button"
                    magnetic={false}
                    variant={vpnUser.status === 'active' ? 'destructive' : 'default'}
                    disabled={vpnActionMutation.isPending}
                    onClick={() => setVpnActionDialog(vpnUser.status === 'active' ? 'disable' : 'enable')}
                  >
                    <Shield className="mr-2 h-4 w-4" />
                    {vpnUser.status === 'active'
                      ? t('detail.vpnDisableTitle')
                      : t('detail.vpnEnableTitle')}
                  </Button>
                </div>
              </>
            )}
          </section>
        </div>

        <div className="grid gap-6 xl:grid-cols-12">
          <section
            id="customer-notes-section"
            className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('detail.notesTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t('detail.notesDescription')}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
                <FileText className="h-4 w-4" />
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.category')}
                </span>
                <select
                  value={noteCategory}
                  onChange={(event) => setNoteCategory(event.target.value as StaffNoteCategory)}
                  className="h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground"
                >
                  {NOTE_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {noteCategoryLabels[category]}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.note')}
                </span>
                <textarea
                  rows={5}
                  value={noteDraft}
                  onChange={(event) => setNoteDraft(event.target.value)}
                  placeholder={t('detail.notePlaceholder')}
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>

              <div className="flex justify-end">
                <Button
                  type="button"
                  magnetic={false}
                  disabled={createNoteMutation.isPending || noteDraft.trim().length === 0}
                  onClick={() => {
                    void createNoteMutation.mutateAsync({
                      category: noteCategory,
                      note: noteDraft,
                    });
                  }}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  {t('common.save')}
                </Button>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {notesQuery.isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div
                    key={index}
                    className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                  />
                ))
              ) : notesQuery.isError ? (
                <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                  {getErrorMessage(notesQuery.error, t('detail.notesLoadError'))}
                </div>
              ) : notesQuery.data?.length ? notesQuery.data.map((note) => (
                <div
                  key={note.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <CustomerStatusChip
                          label={noteCategoryLabels[note.category as StaffNoteCategory] ?? humanizeToken(note.category)}
                          tone={getNoteCategoryTone((note.category as StaffNoteCategory) ?? 'general')}
                        />
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {formatDateTime(note.created_at, locale)}
                        </p>
                      </div>
                      <p className="text-sm font-mono leading-6 text-white">
                        {note.note}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.author')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {note.author?.display_name ?? note.author?.login ?? note.author?.email ?? '--'}
                      </p>
                    </div>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                  {t('detail.notesEmpty')}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('detail.paymentsTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('detail.paymentsDescription')}
            </p>

            <div className="mt-5 space-y-3">
              {paymentsQuery.data?.payments.length ? paymentsQuery.data.payments.map((payment) => (
                <div
                  key={payment.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {formatCurrencyAmount(payment.amount, payment.currency, locale)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        #{shortId(payment.id)} / {payment.provider}
                      </p>
                    </div>
                    <CustomerStatusChip label={payment.status} tone="info" />
                  </div>
                  <p className="mt-3 text-sm font-mono text-muted-foreground">
                    {formatDateTime(payment.created_at, locale)}
                  </p>
                </div>
              )) : (
                <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                  {t('detail.paymentsEmpty')}
                </div>
              )}
            </div>
          </section>
        </div>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('detail.timelineTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('detail.timelineDescription')}
              </p>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-grid-line/20 bg-terminal-bg/45 text-neon-cyan">
              <History className="h-4 w-4" />
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {timelineQuery.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))
            ) : timelineQuery.isError ? (
              <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                {getErrorMessage(timelineQuery.error, t('detail.timelineLoadError'))}
              </div>
            ) : timelineItems.length ? timelineItems.map((item) => {
              const metadataSummary = summarizeTimelineMetadata(item.metadata ?? null);

              return (
                <div
                  key={`${item.kind}-${item.id}`}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                          {item.title}
                        </p>
                        <CustomerStatusChip
                          label={humanizeToken(item.kind)}
                          tone={getTimelineKindTone(item.kind)}
                        />
                        {item.status ? (
                          <CustomerStatusChip
                            label={humanizeToken(item.status)}
                            tone="neutral"
                          />
                        ) : null}
                      </div>
                      {item.description ? (
                        <p className="text-sm font-mono leading-6 text-muted-foreground">
                          {item.description}
                        </p>
                      ) : null}
                      {metadataSummary ? (
                        <p className="text-xs font-mono uppercase tracking-[0.14em] text-muted-foreground">
                          {metadataSummary}
                        </p>
                      ) : null}
                    </div>
                    {item.amount !== null && item.amount !== undefined ? (
                      <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
                        {formatCurrencyAmount(item.amount, item.currency ?? 'USD', locale)}
                      </p>
                    ) : null}
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.occurredAt')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {formatDateTime(item.occurred_at, locale)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.author')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {item.actor_label ?? '--'}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('detail.labels.kind')}
                      </p>
                      <p className="mt-2 text-sm font-mono text-white">
                        {humanizeToken(item.kind)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            }) : (
              <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                {t('detail.timelineEmpty')}
              </div>
            )}
          </div>
        </section>

        <div className="grid gap-6 xl:grid-cols-12">
          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('detail.referralTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('detail.referralDescription')}
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {[
                [t('detail.labels.commissionCount'), String(referralQuery.data?.commission_count ?? 0)],
                [t('detail.labels.referredUsers'), String(referralQuery.data?.referred_users ?? 0)],
                [t('detail.labels.referredBy'), referralQuery.data?.referred_by_user_id ?? '--'],
                [t('common.referralCode'), customer.referral_code ?? '--'],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {label}
                  </p>
                  <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 space-y-3">
              {referralQuery.data?.recent_commissions.length ? referralQuery.data.recent_commissions.slice(0, 5).map((commission) => (
                <div
                  key={commission.id}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                        {formatCurrencyAmount(commission.commission_amount, commission.currency, locale)}
                      </p>
                      <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {commission.referred_user?.email ?? commission.referred_user_id}
                      </p>
                    </div>
                    <CustomerStatusChip label={`${commission.commission_rate}`} tone="warning" />
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                  {t('detail.referralEmpty')}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('detail.partnerTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('detail.partnerDescription')}
            </p>

            {customer.is_partner && partnerQuery.data ? (
              <div className="mt-5 space-y-3">
                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    [t('detail.labels.partnerCodes'), String(partnerQuery.data.code_count)],
                    [t('detail.labels.activeCodes'), String(partnerQuery.data.active_code_count)],
                    [t('detail.labels.partnerClients'), String(partnerQuery.data.total_clients)],
                    [t('detail.labels.lastActivity'), formatDateTime(partnerQuery.data.last_activity_at, locale)],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                    >
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {label}
                      </p>
                      <p className="mt-2 break-all text-sm font-mono text-white">{value}</p>
                    </div>
                  ))}
                </div>

                {partnerQuery.data.codes.map((code) => (
                  <div
                    key={code.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {code.code}
                        </p>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {formatDateTime(code.created_at, locale)}
                        </p>
                      </div>
                      <CustomerStatusChip
                        label={code.is_active ? t('common.active') : t('common.inactive')}
                        tone={code.is_active ? 'success' : 'warning'}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
                {t('detail.partnerEmpty')}
              </div>
            )}
          </section>
        </div>
      </div>

      <AdminActionDialog
        isOpen={activationDialogOpen}
        isPending={updateMutation.isPending}
        title={currentActive ? t('detail.deactivateTitle') : t('detail.activateTitle')}
        description={currentActive ? t('detail.deactivateDescription') : t('detail.activateDescription')}
        confirmLabel={currentActive ? t('common.deactivate') : t('common.reactivate')}
        cancelLabel={t('common.cancel')}
        onClose={() => setActivationDialogOpen(false)}
        onConfirm={async () => {
          await updateMutation.mutateAsync({
            status: currentStatus,
            is_active: !currentActive,
          });
          setActivationDialogOpen(false);
        }}
      />

      <AdminActionDialog
        isOpen={vpnActionDialog !== null}
        isPending={vpnActionMutation.isPending}
        title={vpnActionDialog === 'disable' ? t('detail.vpnDisableTitle') : t('detail.vpnEnableTitle')}
        description={vpnActionDialog === 'disable' ? t('detail.vpnDisableDescription') : t('detail.vpnEnableDescription')}
        confirmLabel={vpnActionDialog === 'disable' ? t('common.deactivate') : t('common.reactivate')}
        cancelLabel={t('common.cancel')}
        reasonLabel={t('detail.dialogs.reasonLabel')}
        reasonPlaceholder={t('detail.dialogs.reasonPlaceholder')}
        subjectLabel={t('common.remnawaveUuid')}
        subject={vpnUser?.remnawave_uuid ?? customer.remnawave_uuid ?? '--'}
        onClose={() => setVpnActionDialog(null)}
        onConfirm={async (reason) => {
          if (!vpnActionDialog) {
            return;
          }

          await vpnActionMutation.mutateAsync({
            mode: vpnActionDialog,
            reason,
          });
        }}
      />

      <AdminActionDialog
        isOpen={deviceToRevoke !== null}
        isPending={revokeDeviceMutation.isPending}
        title={t('detail.revokeDeviceTitle')}
        description={t('detail.revokeDeviceDescription')}
        confirmLabel={t('common.revoke')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('detail.labels.deviceModel')}
        subject={deviceToRevoke ? `${deviceToRevoke.label} / ${deviceToRevoke.platform} / ${deviceToRevoke.appVersion}` : '--'}
        onClose={() => setDeviceToRevoke(null)}
        onConfirm={async () => {
          if (!deviceToRevoke) {
            return;
          }

          await revokeDeviceMutation.mutateAsync(deviceToRevoke.id);
        }}
      />

      <AdminActionDialog
        isOpen={revokeAllDevicesDialogOpen}
        isPending={revokeAllDevicesMutation.isPending}
        title={t('detail.revokeAllDevicesTitle')}
        description={t('detail.revokeAllDevicesDescription')}
        confirmLabel={t('detail.revokeAllDevices')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('common.devices')}
        subject={t('detail.revokeAllDevicesSubject', { count: customer.devices.length })}
        reasonLabel={t('detail.dialogs.reasonLabel')}
        reasonPlaceholder={t('detail.dialogs.reasonPlaceholder')}
        onClose={() => setRevokeAllDevicesDialogOpen(false)}
        onConfirm={async (reason) => {
          await revokeAllDevicesMutation.mutateAsync(reason);
        }}
      />

      <AdminActionDialog
        isOpen={subscriptionResyncDialogOpen}
        isPending={resyncSubscriptionMutation.isPending}
        title={t('detail.resyncSubscriptionTitle')}
        description={t('detail.resyncSubscriptionDescription')}
        confirmLabel={t('detail.resyncSubscription')}
        cancelLabel={t('common.cancel')}
        confirmVariant="default"
        tone="warning"
        subjectLabel={t('detail.labels.upstreamSubscriptionUrl')}
        subject={upstreamSubscriptionUrl ?? '--'}
        reasonLabel={t('detail.dialogs.reasonLabel')}
        reasonPlaceholder={t('detail.dialogs.reasonPlaceholder')}
        onClose={() => setSubscriptionResyncDialogOpen(false)}
        onConfirm={async (reason) => {
          await resyncSubscriptionMutation.mutateAsync(reason);
        }}
      />
    </CustomersPageShell>
  );
}
