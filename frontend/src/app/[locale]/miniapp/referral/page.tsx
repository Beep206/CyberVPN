'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import dynamic from 'next/dynamic';
import { motion } from 'motion/react';
import {
  Copy,
  ExternalLink,
  Gift,
  Link2,
  Loader2,
  Percent,
  QrCode,
  Sparkles,
  Ticket,
  TrendingUp,
  Users,
} from 'lucide-react';
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
} from '@/features/customer-growth/hooks/useCustomerGrowth';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';

const QRCode = dynamic(() => import('react-qr-code'), { ssr: false });

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

export default function MiniAppReferralPage() {
  const t = useTranslations('MiniApp.referral');
  const locale = useLocale();
  const { haptic, hapticNotification, colorScheme, webApp } = useTelegramWebApp();

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
  const referralLink = referralCode ? `https://t.me/cybervpn_bot?start=${referralCode}` : '';

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
    haptic('medium');

    try {
      await navigator.clipboard.writeText(value);
      setCopiedValue(value);
      setTimeout(() => setCopiedValue(null), 1600);
    } catch {
      webApp?.showAlert(t('copyFailed'));
    }
  };

  const shareReferralCode = () => {
    if (!referralCode || !referralLink) {
      return;
    }

    haptic('medium');
    const shareText = t('shareText', { code: referralCode });
    webApp?.openTelegramLink(
      `https://t.me/share/url?url=${encodeURIComponent(referralLink)}&text=${encodeURIComponent(shareText)}`,
    );
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
      hapticNotification('success');

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
      hapticNotification('error');
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
        channel: 'miniapp',
      });

      if (result.invoice?.payment_url) {
        if (webApp?.openInvoice) {
          webApp.openInvoice(result.invoice.payment_url);
        } else {
          webApp?.openLink(result.invoice.payment_url);
        }
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

      hapticNotification('success');
      setGiftRecipientHint('');
      setGiftMessage('');
    } catch (error) {
      hapticNotification('error');
      setGiftPurchaseError(error instanceof Error ? error.message : t('giftPurchase.errors.default'));
    }
  };

  const isDark = colorScheme === 'dark';
  const cardBg = isDark
    ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]'
    : 'bg-[var(--tg-bg-color,oklch(0.96_0.01_250))]';
  const borderColor = isDark
    ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]'
    : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3"
      >
        <Gift className="h-6 w-6 text-neon-pink" />
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
            {t('hubEyebrow')}
          </p>
          <h1 className="text-xl font-display">{t('title')}</h1>
        </div>
      </motion.div>

      {!statusLoading && referralStatus && !referralStatus.enabled ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <p className="font-mono text-sm text-amber-300">{t('programUnavailable')}</p>
        </motion.div>
      ) : null}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-start gap-3">
          <Sparkles className="mt-1 h-5 w-5 text-neon-purple" />
          <div className="flex-1">
            <h2 className="text-lg font-display text-neon-cyan">{t('shareTitle')}</h2>
            <p className="mt-2 text-sm text-muted-foreground font-mono">
              {t('shareDescription')}
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-lg border border-border bg-muted/30 p-4">
          <p className="text-xs text-muted-foreground font-mono mb-2">{t('yourCode')}</p>
          {codeLoading ? (
            <div className="h-10 w-40 animate-pulse rounded bg-muted" />
          ) : (
            <div className="font-mono text-2xl tracking-[0.22em] text-neon-cyan">
              {referralCode || 'N/A'}
            </div>
          )}
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => referralCode && copyValue(referralCode)}
            disabled={!referralCode}
            className="py-2 px-4 bg-neon-cyan text-black rounded-lg hover:bg-neon-cyan/90 transition-colors touch-manipulation flex items-center justify-center gap-2 font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Copy className="h-4 w-4" />
            {copiedValue === referralCode ? t('copied') : t('copyCode')}
          </button>
          <button
            type="button"
            onClick={shareReferralCode}
            disabled={!referralCode}
            className="py-2 px-4 bg-neon-purple text-white rounded-lg hover:bg-neon-purple/90 transition-colors touch-manipulation flex items-center justify-center gap-2 font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Link2 className="h-4 w-4" />
            {t('shareCode')}
          </button>
        </div>
      </motion.div>

      {referralLink ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <div className="flex items-center gap-2 mb-3">
            <QrCode className="h-5 w-5 text-neon-cyan" />
            <h2 className="text-sm font-display">{t('qrCodeTitle')}</h2>
          </div>
          <div className="flex justify-center p-4 bg-white rounded-lg">
            <QRCode value={referralLink} size={200} level="M" fgColor="#000000" bgColor="#FFFFFF" />
          </div>
          <p className="text-xs text-muted-foreground text-center mt-3 font-mono">
            {t('qrCodeHint')}
          </p>
        </motion.div>
      ) : null}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-2 gap-2"
      >
        <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
          <div className="flex items-center gap-2 mb-2">
            <Gift className="h-4 w-4 text-neon-pink" />
            <span className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground font-mono">
              {t('overview.activeInvites')}
            </span>
          </div>
          <div className="text-2xl font-display text-neon-pink">
            {invitesLoading ? '...' : overview.activeInvites}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground font-mono">
            {t('overview.activeInvitesHint')}
          </p>
        </div>

        <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
          <div className="flex items-center gap-2 mb-2">
            <Users className="h-4 w-4 text-neon-cyan" />
            <span className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground font-mono">
              {t('overview.totalReferrals')}
            </span>
          </div>
          <div className="text-2xl font-display text-neon-cyan">
            {statsLoading ? '...' : overview.totalReferrals}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground font-mono">
            {t('overview.totalReferralsHint')}
          </p>
        </div>

        <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-4 w-4 text-matrix-green" />
            <span className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground font-mono">
              {t('overview.totalRewards')}
            </span>
          </div>
          <div className="text-2xl font-display text-matrix-green">
            {statsLoading ? '...' : formatCurrency(locale, overview.totalEarned)}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground font-mono">
            {t('overview.totalRewardsHint')}
          </p>
        </div>

        <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
          <div className="flex items-center gap-2 mb-2">
            <Percent className="h-4 w-4 text-neon-purple" />
            <span className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground font-mono">
              {t('overview.currentRate')}
            </span>
          </div>
          <div className="text-2xl font-display text-neon-purple">
            {statusLoading && statsLoading ? '...' : `${overview.currentRate}%`}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground font-mono">
            {t('overview.currentRateHint')}
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18 }}
      >
        <GrowthNotificationsPanel
          surface="miniapp"
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
            haptic('light');
          }}
          onCloseDetail={() => {
            setNotificationRecoveryError('');
            setNotificationSupportError('');
            setSelectedNotificationId(null);
          }}
          onToggleArchived={() => {
            setIncludeArchivedNotifications((current) => !current);
            haptic('light');
          }}
          onRequestRecovery={(notificationId, deliveryChannel) => {
            setNotificationRecoveryError('');
            requestGrowthNotificationRecovery.mutate(
              { notificationId, deliveryChannel },
              {
                onError: (error) => {
                  setNotificationRecoveryError(getGrowthNotificationRecoveryErrorMessage(error));
                  hapticNotification('error');
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
                  haptic('medium');
                  if (actionLink.external) {
                    if (actionLink.href.startsWith('https://t.me/')) {
                      webApp?.openTelegramLink(actionLink.href);
                      return;
                    }
                    webApp?.openLink(actionLink.href);
                    return;
                  }
                  window.location.assign(actionLink.href);
                },
                onError: (error) => {
                  setNotificationSupportError(
                    getGrowthNotificationSupportEscalationErrorMessage(error),
                  );
                  hapticNotification('error');
                },
              },
            );
          }}
          onMarkRead={(notificationId) => {
            haptic('light');
            markGrowthNotificationRead.mutate(notificationId);
          }}
          onArchive={(notificationId) => {
            haptic('light');
            archiveGrowthNotification.mutate(notificationId);
          }}
        />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.19 }}
      >
        <GrowthNotificationPreferencesPanel
          t={t}
          preferences={growthNotificationPreferences}
          isLoading={preferencesLoading}
          isSaving={updateGrowthNotificationPreferences.isPending}
          onToggle={(key, nextValue) => {
            haptic('light');
            updateGrowthNotificationPreferences.mutate({ [key]: nextValue });
          }}
          variant="miniapp"
        />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <Ticket className="h-5 w-5 text-neon-purple" />
          <div>
            <h2 className="text-sm font-display">{t('redeemTitle')}</h2>
            <p className="text-xs text-muted-foreground font-mono mt-1">{t('redeemSubtitle')}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label
              htmlFor="miniapp-growth-code"
              className="text-xs text-muted-foreground font-mono block mb-2"
            >
              {t('redeemInputLabel')}
            </label>
            <input
              id="miniapp-growth-code"
              value={redeemCode}
              onChange={(event) => setRedeemCode(event.target.value.toUpperCase())}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  void handleRedeemCode();
                }
              }}
              placeholder={t('redeemPlaceholder')}
              disabled={redeemGrowthCode.isPending}
              className="w-full rounded-lg border border-border bg-muted px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-neon-purple"
            />
          </div>

          {redeemError ? (
            <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm font-mono text-amber-300">
              {redeemError}
            </div>
          ) : null}

          {redeemSuccess ? (
            <div className="rounded-lg border border-matrix-green/30 bg-matrix-green/10 px-4 py-3 text-sm font-mono text-matrix-green">
              {redeemSuccess}
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => void handleRedeemCode()}
            disabled={redeemGrowthCode.isPending || !redeemCode.trim()}
            className="w-full py-3 px-4 bg-neon-purple text-white rounded-lg hover:bg-neon-purple/90 transition-colors touch-manipulation font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {redeemGrowthCode.isPending ? t('redeeming') : t('redeemButton')}
          </button>
        </div>

        <div className="mt-4 rounded-lg border border-border bg-muted/30 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground font-mono">
            {t('promoNoteTitle')}
          </p>
          <p className="mt-2 text-xs text-muted-foreground font-mono">{t('promoNoteBody')}</p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.23 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <ExternalLink className="h-5 w-5 text-neon-cyan" />
          <div>
            <h2 className="text-sm font-display">{t('giftPurchase.title')}</h2>
            <p className="text-xs text-muted-foreground font-mono mt-1">{t('giftPurchase.subtitle')}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label htmlFor="miniapp-gift-plan" className="text-xs text-muted-foreground font-mono block mb-2">
              {t('giftPurchase.planLabel')}
            </label>
            <select
              id="miniapp-gift-plan"
              value={giftPlanId}
              onChange={(event) => setGiftPlanId(event.target.value)}
              disabled={giftPlansLoading || giftPurchase.isPending}
              className="w-full rounded-lg border border-border bg-muted px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-neon-cyan"
            >
              <option value="">{t('giftPurchase.planPlaceholder')}</option>
              {eligibleGiftPlans.map((plan) => (
                <option key={plan.uuid} value={plan.uuid}>
                  {`${plan.display_name} · ${plan.duration_days}d · ${formatCurrency(locale, plan.price_usd)}`}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="miniapp-gift-recipient" className="text-xs text-muted-foreground font-mono block mb-2">
              {t('giftPurchase.recipientHintLabel')}
            </label>
            <input
              id="miniapp-gift-recipient"
              value={giftRecipientHint}
              onChange={(event) => setGiftRecipientHint(event.target.value)}
              placeholder={t('giftPurchase.recipientHintPlaceholder')}
              disabled={giftPurchase.isPending}
              className="w-full rounded-lg border border-border bg-muted px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-neon-cyan"
            />
          </div>

          <div>
            <label htmlFor="miniapp-gift-message" className="text-xs text-muted-foreground font-mono block mb-2">
              {t('giftPurchase.messageLabel')}
            </label>
            <textarea
              id="miniapp-gift-message"
              rows={3}
              value={giftMessage}
              onChange={(event) => setGiftMessage(event.target.value)}
              placeholder={t('giftPurchase.messagePlaceholder')}
              disabled={giftPurchase.isPending}
              className="w-full rounded-lg border border-border bg-muted px-4 py-3 font-mono text-sm outline-none transition-colors focus:border-neon-cyan"
            />
          </div>

          {giftPurchaseError ? (
            <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm font-mono text-amber-300">
              {giftPurchaseError}
            </div>
          ) : null}

          {giftPurchaseSuccess ? (
            <div className="rounded-lg border border-matrix-green/30 bg-matrix-green/10 px-4 py-3 text-sm font-mono text-matrix-green">
              {giftPurchaseSuccess}
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => void handleGiftPurchase()}
            disabled={giftPurchase.isPending}
            className="w-full py-3 px-4 bg-neon-cyan text-black rounded-lg hover:bg-neon-cyan/90 transition-colors touch-manipulation font-mono disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <Gift className="h-5 w-5 text-neon-cyan" />
          <div>
            <h2 className="text-sm font-display">{t('invitesTitle')}</h2>
            <p className="text-xs text-muted-foreground font-mono mt-1">{t('invitesSubtitle')}</p>
          </div>
        </div>

        {invitesLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-neon-cyan" />
          </div>
        ) : invites.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4 font-mono">{t('noInvites')}</p>
        ) : (
          <div className="space-y-2">
            {invites.map((invite) => {
              const expired = isInviteExpired(invite.expires_at);
              const status = invite.is_used ? 'used' : expired ? 'expired' : 'active';

              return (
                <div key={invite.id} className="p-3 bg-muted/40 rounded-lg border border-border/60">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <code className="font-mono text-sm text-neon-cyan">{invite.code}</code>
                        <span
                          className={`rounded-full px-2 py-1 text-[10px] font-mono uppercase tracking-[0.16em] ${
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
                      <div className="mt-2 space-y-1 text-xs text-muted-foreground font-mono">
                        <div>{t('inviteDays', { days: invite.free_days })}</div>
                        <div>{t('inviteExpires', { date: formatDate(locale, invite.expires_at) })}</div>
                        <div>{t('inviteCreated', { date: formatDate(locale, invite.created_at) })}</div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => void copyValue(invite.code)}
                      className="p-2 bg-neon-cyan/10 text-neon-cyan rounded-lg hover:bg-neon-cyan/20 transition-colors touch-manipulation"
                      aria-label={t('copyCode')}
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.28 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <Gift className="h-5 w-5 text-neon-pink" />
          <div>
            <h2 className="text-sm font-display">{t('giftsTitle')}</h2>
            <p className="text-xs text-muted-foreground font-mono mt-1">{t('giftsSubtitle')}</p>
          </div>
        </div>

        {giftsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-neon-cyan" />
          </div>
        ) : gifts.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4 font-mono">{t('noGifts')}</p>
        ) : (
          <div className="space-y-2">
            {gifts.map((gift) => {
              const visibleCode = gift.raw_code ?? gift.masked_code;
              const status = formatGiftStatus(gift.status);

              return (
                <div key={gift.id} className="p-3 bg-muted/40 rounded-lg border border-border/60">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <code className="font-mono text-sm text-neon-pink">{visibleCode}</code>
                        <span
                          className={`rounded-full px-2 py-1 text-[10px] font-mono uppercase tracking-[0.16em] ${
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
                      <div className="mt-2 space-y-1 text-xs text-muted-foreground font-mono">
                        <div>{t('giftPlan', { plan: gift.plan_family ?? 'N/A', days: gift.duration_days ?? 0 })}</div>
                        <div>{t('giftCreated', { date: formatDate(locale, gift.created_at) })}</div>
                        <div>{t('giftRecipient', { recipient: gift.recipient_hint ?? t('giftRecipientFallback') })}</div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => void copyValue(visibleCode)}
                      className="p-2 bg-neon-pink/10 text-neon-pink rounded-lg hover:bg-neon-pink/20 transition-colors touch-manipulation"
                      aria-label={t('copyCode')}
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-5 w-5 text-matrix-green" />
          <div>
            <h2 className="text-sm font-display">{t('activityTitle')}</h2>
            <p className="text-xs text-muted-foreground font-mono mt-1">{t('activitySubtitle')}</p>
          </div>
        </div>

        {activityLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-neon-cyan" />
          </div>
        ) : activity.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4 font-mono">{t('noActivity')}</p>
        ) : (
          <div className="space-y-2">
            {activity.map((entry) => (
              <div
                key={entry.id}
                className="p-3 bg-muted/40 rounded-lg border border-border/60"
              >
                <p className="text-sm font-mono text-neon-cyan">
                  {t('activityReward', {
                    amount: formatCurrency(locale, entry.commission_amount),
                  })}
                </p>
                <p className="mt-1 text-xs text-muted-foreground font-mono">
                  {t('activityBase', {
                    amount: formatCurrency(locale, entry.base_amount),
                    rate: entry.commission_rate,
                  })}
                </p>
                <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground font-mono">
                  {formatDate(locale, entry.created_at)}
                </p>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
