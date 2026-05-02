'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import {
  Copy,
  ExternalLink,
  Gift,
  Link2,
  Loader2,
  Percent,
  Sparkles,
  Ticket,
  TrendingUp,
  Users,
} from 'lucide-react';
import { AxiosError } from 'axios';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { GrowthNotificationsPanel } from '@/features/customer-growth/components/GrowthNotificationsPanel';
import { GrowthNotificationPreferencesPanel } from '@/features/customer-growth/components/GrowthNotificationPreferencesPanel';
import type { GiftCodeRecord } from '@/features/customer-growth/hooks/useCustomerGrowth';
import {
  useArchiveGrowthNotification,
  getGrowthNotificationRecoveryErrorMessage,
  getGrowthNotificationSupportEscalationErrorMessage,
  getGrowthRedeemErrorMessage,
  useGiftCatalogPlans,
  useGiftCodes,
  useGiftPurchase,
  useGrowthNotificationCounters,
  useGrowthNotificationDetail,
  useGrowthNotifications,
  useGrowthNotificationPreferences,
  useInviteCodes,
  useMarkGrowthNotificationRead,
  useRecentReferralActivity,
  useRedeemGrowthCode,
  useRequestGrowthNotificationRecovery,
  useRequestGrowthNotificationSupportEscalation,
  useReferralCode,
  useReferralStats,
  useReferralStatus,
  useUpdateGrowthNotificationPreferences,
} from '../hooks/useReferral';

type InviteCode = {
  id: string;
  code: string;
  free_days: number;
  is_used: boolean;
  expires_at: string | null;
  created_at: string;
};

type ReferralActivity = {
  id: string;
  commission_amount: number;
  base_amount: number;
  commission_rate: number;
  created_at: string;
};

function isInviteExpired(expiresAt?: string | null): boolean {
  return Boolean(expiresAt && new Date(expiresAt).getTime() <= Date.now());
}

function formatDate(locale: string, value?: string | null): string {
  if (!value) {
    return 'N/A';
  }

  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

function formatCurrency(locale: string, amount: number): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

function formatGiftStatus(status: string): 'active' | 'redeemed' | 'expired' | 'revoked' {
  if (status === 'redeemed') {
    return 'redeemed';
  }
  if (status === 'expired') {
    return 'expired';
  }
  if (status === 'revoked') {
    return 'revoked';
  }
  return 'active';
}

export function ReferralClient() {
  const t = useTranslations('Referral');
  const locale = useLocale();
  const [redeemCode, setRedeemCode] = useState('');
  const [redeemError, setRedeemError] = useState('');
  const [redeemSuccess, setRedeemSuccess] = useState('');
  const [copiedValue, setCopiedValue] = useState<string | null>(null);
  const [giftPlanId, setGiftPlanId] = useState('');
  const [giftRecipientHint, setGiftRecipientHint] = useState('');
  const [giftMessage, setGiftMessage] = useState('');
  const [giftPurchaseError, setGiftPurchaseError] = useState('');
  const [giftPurchaseSuccess, setGiftPurchaseSuccess] = useState('');
  const [includeArchivedNotifications, setIncludeArchivedNotifications] = useState(false);
  const [selectedNotificationId, setSelectedNotificationId] = useState<string | null>(null);
  const [notificationRecoveryError, setNotificationRecoveryError] = useState('');
  const [notificationSupportError, setNotificationSupportError] = useState('');

  const { data: referralCodeData, isLoading: codeLoading } = useReferralCode();
  const { data: referralStats, isLoading: statsLoading } = useReferralStats();
  const { data: referralStatus, isLoading: statusLoading } = useReferralStatus();
  const { data: inviteCodes, isLoading: invitesLoading } = useInviteCodes();
  const { data: giftCodes, isLoading: giftsLoading } = useGiftCodes();
  const { data: giftPlans, isLoading: giftPlansLoading } = useGiftCatalogPlans();
  const { data: recentActivity, isLoading: activityLoading } = useRecentReferralActivity();
  const { data: growthNotifications, isLoading: notificationsLoading } =
    useGrowthNotifications(includeArchivedNotifications);
  const { data: growthNotificationCounters } = useGrowthNotificationCounters();
  const { data: growthNotificationPreferences, isLoading: preferencesLoading } =
    useGrowthNotificationPreferences();
  const { data: growthNotificationDetail, isLoading: notificationDetailLoading } =
    useGrowthNotificationDetail(selectedNotificationId);
  const redeemGrowthCode = useRedeemGrowthCode();
  const giftPurchase = useGiftPurchase();
  const markGrowthNotificationRead = useMarkGrowthNotificationRead();
  const archiveGrowthNotification = useArchiveGrowthNotification();
  const updateGrowthNotificationPreferences = useUpdateGrowthNotificationPreferences();
  const requestGrowthNotificationRecovery = useRequestGrowthNotificationRecovery();
  const requestGrowthNotificationSupportEscalation =
    useRequestGrowthNotificationSupportEscalation();

  const referralCode = referralCodeData?.referral_code ?? '';
  const invites = useMemo(() => (inviteCodes ?? []) as InviteCode[], [inviteCodes]);
  const gifts = useMemo(() => (giftCodes ?? []) as GiftCodeRecord[], [giftCodes]);
  const activity = useMemo(
    () => (recentActivity ?? []) as ReferralActivity[],
    [recentActivity],
  );
  const eligibleGiftPlans = useMemo(() => giftPlans ?? [], [giftPlans]);

  const overview = useMemo(() => {
    const activeInvites = invites.filter(
      (invite) => !invite.is_used && !isInviteExpired(invite.expires_at),
    ).length;

    return {
      activeInvites,
      totalReferrals: referralStats?.total_referrals ?? 0,
      totalEarned: referralStats?.total_earned ?? 0,
      currentRate: referralStatus?.commission_rate ?? referralStats?.commission_rate ?? 0,
    };
  }, [invites, referralStats, referralStatus]);

  const copyValue = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedValue(value);
      setTimeout(() => setCopiedValue(null), 1600);
    } catch {
      setCopiedValue(null);
    }
  };

  const shareReferralCode = async () => {
    if (!referralCode) {
      return;
    }

    const shareText = t('shareMessage', { code: referralCode });

    if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
      try {
        await navigator.share({
          title: t('shareTitle'),
          text: shareText,
        });
        return;
      } catch {
        // Fall through to clipboard when the share sheet is dismissed.
      }
    }

    await copyValue(shareText);
  };

  const handleRedeemCode = async () => {
    const normalizedCode = redeemCode.trim().toUpperCase();
    if (!normalizedCode) {
      setRedeemError(t('redeemErrors.empty'));
      return;
    }

    setRedeemError('');
    setRedeemSuccess('');

    try {
      const redeemed = await redeemGrowthCode.mutateAsync(normalizedCode);
      setRedeemCode('');

      if (redeemed.codeType === 'invite') {
        setRedeemSuccess(
          t('redeemSuccessInvite', {
            days: redeemed.inviteCode.free_days,
          }),
        );
        return;
      }

      setRedeemSuccess(
        t('redeemSuccessGift', {
          plan: redeemed.giftRedemption.gift_code.plan_family ?? 'gift plan',
          days: redeemed.giftRedemption.gift_code.duration_days ?? 0,
        }),
      );
    } catch (error) {
      setRedeemError(getGrowthRedeemErrorMessage(error));
    }
  };

  const handleGiftPurchase = async () => {
    if (!giftPlanId) {
      setGiftPurchaseError(t('giftPurchase.errors.planRequired'));
      return;
    }

    setGiftPurchaseError('');
    setGiftPurchaseSuccess('');

    try {
      const result = await giftPurchase.mutateAsync({
        plan_id: giftPlanId,
        recipient_hint: giftRecipientHint.trim() || null,
        gift_message: giftMessage.trim() || null,
        channel: 'web',
      });

      if (result.invoice?.payment_url) {
        window.open(result.invoice.payment_url, '_blank', 'noopener,noreferrer');
        setGiftPurchaseSuccess(t('giftPurchase.successPaymentPending'));
      } else if (result.gift_code?.raw_code || result.gift_code?.masked_code) {
        setGiftPurchaseSuccess(
          t('giftPurchase.successIssued', {
            code: result.gift_code?.raw_code ?? result.gift_code?.masked_code ?? 'N/A',
          }),
        );
      } else {
        setGiftPurchaseSuccess(t('giftPurchase.successQueued'));
      }

      setGiftRecipientHint('');
      setGiftMessage('');
    } catch (error) {
      const detail =
        error instanceof AxiosError && typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : null;
      setGiftPurchaseError(detail || t('giftPurchase.errors.default'));
    }
  };

  return (
    <div className="space-y-8">
      {!statusLoading && referralStatus && !referralStatus.enabled ? (
        <div className="cyber-card border-amber-400/30 bg-amber-400/8 p-5">
          <p className="font-mono text-sm text-amber-300">{t('programUnavailable')}</p>
        </div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <div className="cyber-card p-8">
          <div className="flex items-center gap-3">
            <Sparkles className="h-7 w-7 text-neon-purple" />
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground">
                {t('hubEyebrow')}
              </p>
              <h2 className="mt-2 text-2xl font-display text-neon-cyan">{t('shareTitle')}</h2>
            </div>
          </div>

          <p className="mt-4 max-w-2xl text-sm text-muted-foreground">{t('shareDescription')}</p>

          <div className="mt-6 flex flex-col gap-4 md:flex-row">
            <div className="flex-1 rounded-2xl border border-grid-line/30 bg-terminal-surface px-6 py-5">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                {t('yourCode')}
              </p>
              {codeLoading ? (
                <div className="mt-3 h-10 w-40 animate-pulse rounded bg-grid-line/20" />
              ) : (
                <div className="mt-3 font-mono text-3xl tracking-[0.35em] text-neon-cyan">
                  {referralCode || 'N/A'}
                </div>
              )}
            </div>

            <div className="grid gap-3 md:w-56">
              <button
                type="button"
                onClick={() => referralCode && copyValue(referralCode)}
                disabled={!referralCode}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-3 text-sm font-mono text-neon-cyan transition-colors hover:bg-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Copy className="h-4 w-4" />
                {copiedValue === referralCode ? t('copied') : t('copyCode')}
              </button>

              <button
                type="button"
                onClick={shareReferralCode}
                disabled={!referralCode}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-neon-purple/40 bg-neon-purple/10 px-4 py-3 text-sm font-mono text-neon-purple transition-colors hover:bg-neon-purple/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Link2 className="h-4 w-4" />
                {t('shareCode')}
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <div className="cyber-card p-5">
            <div className="flex items-center gap-2">
              <Gift className="h-5 w-5 text-neon-pink" />
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.activeInvites')}
              </p>
            </div>
            <div className="mt-4 text-4xl font-display text-neon-pink">
              {invitesLoading ? '...' : overview.activeInvites}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{t('overview.activeInvitesHint')}</p>
          </div>

          <div className="cyber-card p-5">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-neon-cyan" />
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.totalReferrals')}
              </p>
            </div>
            <div className="mt-4 text-4xl font-display text-neon-cyan">
              {statsLoading ? '...' : overview.totalReferrals}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{t('overview.totalReferralsHint')}</p>
          </div>

          <div className="cyber-card p-5">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-matrix-green" />
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.totalRewards')}
              </p>
            </div>
            <div className="mt-4 text-4xl font-display text-matrix-green">
              {statsLoading ? '...' : formatCurrency(locale, overview.totalEarned)}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{t('overview.totalRewardsHint')}</p>
          </div>

          <div className="cyber-card p-5">
            <div className="flex items-center gap-2">
              <Percent className="h-5 w-5 text-neon-purple" />
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.currentRate')}
              </p>
            </div>
            <div className="mt-4 text-4xl font-display text-neon-purple">
              {statusLoading && statsLoading ? '...' : `${overview.currentRate}%`}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{t('overview.currentRateHint')}</p>
          </div>
        </div>
      </section>

      <GrowthNotificationsPanel
        surface="dashboard"
        locale={locale}
        t={t}
        items={growthNotifications ?? []}
        counters={growthNotificationCounters}
        includeArchived={includeArchivedNotifications}
        isLoading={notificationsLoading}
        isMarkingRead={markGrowthNotificationRead.isPending}
        isArchiving={archiveGrowthNotification.isPending}
        isDetailLoading={notificationDetailLoading}
        isRecovering={requestGrowthNotificationRecovery.isPending}
        isEscalatingSupport={requestGrowthNotificationSupportEscalation.isPending}
        recoveryError={notificationRecoveryError}
        supportError={notificationSupportError}
        selectedNotificationId={selectedNotificationId}
        detail={growthNotificationDetail ?? null}
        onInspect={(notificationId) => {
          setNotificationRecoveryError('');
          setNotificationSupportError('');
          setSelectedNotificationId(notificationId);
        }}
        onCloseDetail={() => {
          setNotificationRecoveryError('');
          setNotificationSupportError('');
          setSelectedNotificationId(null);
        }}
        onToggleArchived={() => setIncludeArchivedNotifications((current) => !current)}
        onRequestRecovery={(notificationId, deliveryChannel) => {
          setNotificationRecoveryError('');
          requestGrowthNotificationRecovery.mutate(
            { notificationId, deliveryChannel },
            {
              onError: (error) => {
                setNotificationRecoveryError(getGrowthNotificationRecoveryErrorMessage(error));
              },
            },
          );
        }}
        onEscalateSupport={(notificationId, actionLink) => {
          setNotificationSupportError('');
          requestGrowthNotificationSupportEscalation.mutate(
            {
              notificationId,
              deliveryChannel: actionLink.deliveryChannel ?? null,
              escalationChannel: actionLink.escalationChannel ?? 'contact_form',
            },
            {
              onSuccess: () => {
                if (actionLink.external) {
                  window.open(actionLink.href, '_blank', 'noopener,noreferrer');
                  return;
                }
                window.location.assign(actionLink.href);
              },
              onError: (error) => {
                setNotificationSupportError(
                  getGrowthNotificationSupportEscalationErrorMessage(error),
                );
              },
            },
          );
        }}
        onMarkRead={(notificationId) => markGrowthNotificationRead.mutate(notificationId)}
        onArchive={(notificationId) => archiveGrowthNotification.mutate(notificationId)}
      />

      <GrowthNotificationPreferencesPanel
        t={t}
        preferences={growthNotificationPreferences}
        isLoading={preferencesLoading}
        isSaving={updateGrowthNotificationPreferences.isPending}
        onToggle={(key, nextValue) =>
          updateGrowthNotificationPreferences.mutate({ [key]: nextValue })
        }
      />

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="cyber-card p-6">
          <div className="flex items-center gap-3">
            <Ticket className="h-6 w-6 text-neon-purple" />
            <div>
              <h2 className="text-xl font-display text-neon-purple">{t('redeemTitle')}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t('redeemSubtitle')}</p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <CyberInput
              label={t('redeemInputLabel')}
              type="text"
              value={redeemCode}
              onChange={(event) => setRedeemCode(event.target.value.toUpperCase())}
              placeholder={t('redeemPlaceholder')}
              prefix="redeem"
              disabled={redeemGrowthCode.isPending}
              error={redeemError}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  void handleRedeemCode();
                }
              }}
            />

            {redeemSuccess ? (
              <div className="rounded-xl border border-matrix-green/30 bg-matrix-green/10 px-4 py-3 text-sm font-mono text-matrix-green">
                {redeemSuccess}
              </div>
            ) : null}

            <button
              type="button"
              onClick={() => void handleRedeemCode()}
              disabled={redeemGrowthCode.isPending || !redeemCode.trim()}
              className="inline-flex w-full items-center justify-center rounded-xl border border-neon-purple/40 bg-neon-purple/10 px-4 py-3 text-sm font-mono text-neon-purple transition-colors hover:bg-neon-purple/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {redeemGrowthCode.isPending ? t('redeeming') : t('redeemButton')}
            </button>
          </div>

          <div className="mt-6 rounded-2xl border border-grid-line/30 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              {t('promoNoteTitle')}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">{t('promoNoteBody')}</p>
          </div>
        </div>

        <div className="cyber-card p-6">
          <div className="flex items-center gap-3">
            <Gift className="h-6 w-6 text-neon-cyan" />
            <div>
              <h2 className="text-xl font-display text-neon-cyan">{t('giftPurchase.title')}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t('giftPurchase.subtitle')}</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('giftPurchase.planLabel')}
              </span>
              <select
                value={giftPlanId}
                onChange={(event) => setGiftPlanId(event.target.value)}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                disabled={giftPlansLoading || giftPurchase.isPending}
              >
                <option value="">{t('giftPurchase.planPlaceholder')}</option>
                {eligibleGiftPlans.map((plan) => (
                  <option key={plan.uuid} value={plan.uuid}>
                    {`${plan.display_name} · ${plan.duration_days}d · ${formatCurrency(locale, plan.price_usd)}`}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('giftPurchase.recipientHintLabel')}
              </span>
              <input
                value={giftRecipientHint}
                onChange={(event) => setGiftRecipientHint(event.target.value)}
                placeholder={t('giftPurchase.recipientHintPlaceholder')}
                disabled={giftPurchase.isPending}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                {t('giftPurchase.messageLabel')}
              </span>
              <textarea
                rows={3}
                value={giftMessage}
                onChange={(event) => setGiftMessage(event.target.value)}
                placeholder={t('giftPurchase.messagePlaceholder')}
                disabled={giftPurchase.isPending}
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            {giftPurchaseError ? (
              <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                {giftPurchaseError}
              </div>
            ) : null}

            {giftPurchaseSuccess ? (
              <div className="rounded-xl border border-matrix-green/30 bg-matrix-green/10 px-4 py-3 text-sm font-mono text-matrix-green">
                {giftPurchaseSuccess}
              </div>
            ) : null}

            <button
              type="button"
              onClick={() => void handleGiftPurchase()}
              disabled={giftPurchase.isPending}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-neon-cyan/40 bg-neon-cyan/10 px-4 py-3 text-sm font-mono text-neon-cyan transition-colors hover:bg-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {giftPurchase.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('giftPurchase.processing')}
                </>
              ) : (
                <>
                  <ExternalLink className="h-4 w-4" />
                  {t('giftPurchase.action')}
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="cyber-card p-6">
          <div className="flex items-center gap-3">
            <Gift className="h-6 w-6 text-neon-cyan" />
            <div>
              <h2 className="text-xl font-display text-neon-cyan">{t('invitesTitle')}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t('invitesSubtitle')}</p>
            </div>
          </div>

          {invitesLoading ? (
            <div className="mt-6 space-y-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-20 animate-pulse rounded-2xl bg-grid-line/15" />
              ))}
            </div>
          ) : invites.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-grid-line/30 bg-white/[0.03] p-6 text-center">
              <p className="font-mono text-sm text-muted-foreground">{t('noInvites')}</p>
            </div>
          ) : (
            <div className="mt-6 space-y-3">
              {invites.map((invite) => {
                const expired = isInviteExpired(invite.expires_at);
                const status = invite.is_used ? 'used' : expired ? 'expired' : 'active';

                return (
                  <div
                    key={invite.id}
                    className="rounded-2xl border border-grid-line/30 bg-white/[0.03] p-4"
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <code className="font-mono text-lg tracking-[0.2em] text-neon-cyan">
                            {invite.code}
                          </code>
                          <span
                            className={`rounded-full px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] ${
                              status === 'active'
                                ? 'bg-matrix-green/15 text-matrix-green'
                                : status === 'used'
                                  ? 'bg-neon-purple/15 text-neon-purple'
                                  : 'bg-amber-400/15 text-amber-300'
                            }`}
                          >
                            {t(`inviteStatus.${status}`)}
                          </span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
                          <span>{t('inviteDays', { days: invite.free_days })}</span>
                          <span>{t('inviteExpires', { date: formatDate(locale, invite.expires_at) })}</span>
                          <span>{t('inviteCreated', { date: formatDate(locale, invite.created_at) })}</span>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => void copyValue(invite.code)}
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-3 text-sm font-mono text-neon-cyan transition-colors hover:bg-neon-cyan/20"
                      >
                        <Copy className="h-4 w-4" />
                        {copiedValue === invite.code ? t('copied') : t('copyCode')}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="cyber-card p-6">
          <div className="flex items-center gap-3">
            <Gift className="h-6 w-6 text-neon-pink" />
            <div>
              <h2 className="text-xl font-display text-neon-pink">{t('giftsTitle')}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t('giftsSubtitle')}</p>
            </div>
          </div>

          {giftsLoading ? (
            <div className="mt-6 space-y-3">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-20 animate-pulse rounded-2xl bg-grid-line/15" />
              ))}
            </div>
          ) : gifts.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-grid-line/30 bg-white/[0.03] p-6 text-center">
              <p className="font-mono text-sm text-muted-foreground">{t('noGifts')}</p>
            </div>
          ) : (
            <div className="mt-6 space-y-3">
              {gifts.map((gift) => {
                const visibleCode = gift.raw_code ?? gift.masked_code;
                const status = formatGiftStatus(gift.status);

                return (
                  <div
                    key={gift.id}
                    className="rounded-2xl border border-grid-line/30 bg-white/[0.03] p-4"
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-3">
                          <code className="font-mono text-lg tracking-[0.14em] text-neon-pink">
                            {visibleCode}
                          </code>
                          <span
                            className={`rounded-full px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] ${
                              status === 'active'
                                ? 'bg-neon-cyan/15 text-neon-cyan'
                                : status === 'redeemed'
                                  ? 'bg-matrix-green/15 text-matrix-green'
                                  : status === 'revoked'
                                    ? 'bg-neon-purple/15 text-neon-purple'
                                    : 'bg-amber-400/15 text-amber-300'
                            }`}
                          >
                            {t(`giftStatus.${status}`)}
                          </span>
                        </div>

                        <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
                          <span>
                            {t('giftPlan', {
                              plan: gift.plan_family ?? 'N/A',
                              days: gift.duration_days ?? 0,
                            })}
                          </span>
                          <span>{t('giftCreated', { date: formatDate(locale, gift.created_at) })}</span>
                          <span>
                            {t('giftRecipient', {
                              recipient: gift.recipient_hint ?? t('giftRecipientFallback'),
                            })}
                          </span>
                          {gift.redeemed_at ? (
                            <span>{t('giftRedeemed', { date: formatDate(locale, gift.redeemed_at) })}</span>
                          ) : null}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => visibleCode && void copyValue(visibleCode)}
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink transition-colors hover:bg-neon-pink/20"
                      >
                        <Copy className="h-4 w-4" />
                        {copiedValue === visibleCode ? t('copied') : t('copyCode')}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section className="cyber-card p-6">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-6 w-6 text-matrix-green" />
          <div>
            <h2 className="text-xl font-display text-matrix-green">{t('activityTitle')}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t('activitySubtitle')}</p>
          </div>
        </div>

        {activityLoading ? (
          <div className="mt-6 space-y-3">
            {[0, 1, 2].map((item) => (
              <div key={item} className="h-20 animate-pulse rounded-2xl bg-grid-line/15" />
            ))}
          </div>
        ) : activity.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-grid-line/30 bg-white/[0.03] p-6 text-center">
            <p className="font-mono text-sm text-muted-foreground">{t('noActivity')}</p>
          </div>
        ) : (
          <div className="mt-6 space-y-3">
            {activity.map((entry) => (
              <div
                key={entry.id}
                className="flex flex-col gap-3 rounded-2xl border border-grid-line/30 bg-white/[0.03] p-4 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <p className="font-mono text-sm text-white/85">
                    {t('activityReward', {
                      amount: formatCurrency(locale, entry.commission_amount),
                    })}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t('activityBase', {
                      amount: formatCurrency(locale, entry.base_amount),
                      rate: entry.commission_rate,
                    })}
                  </p>
                </div>

                <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  {formatDate(locale, entry.created_at)}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
