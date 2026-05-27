'use client';

import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { invitesApi, miniappApi } from '@/lib/api';
import { motion } from 'motion/react';
import {
  AlertTriangle,
  Check,
  Shield,
  Zap,
  CreditCard,
  Settings,
  TrendingUp,
  Clock,
  Server,
  Gift,
  ExternalLink,
  Loader2,
  Users,
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { Link } from '@/i18n/navigation';
import { VpnConfigCard } from '../components/VpnConfigCard';
import { emitMiniAppRuntimeEvent } from '@/features/miniapp-runtime/lib/runtime-analytics';
import { useCustomerSubscriptions } from '@/features/customer-subscriptions/customer-subscription-context';

function formatBytes(bytes?: number | null) {
  if (!bytes) return '0 GB';
  const gb = bytes / (1024 ** 3);
  return `${gb.toFixed(2)} GB`;
}

function translateOrFallback(t: ReturnType<typeof useTranslations>, key: string, fallback: string) {
  const translated = t(key);
  return translated === key ? fallback : translated;
}

/**
 * Mini App Home/Dashboard page
 * Renders from the dedicated bootstrap/read model instead of broad API fan-out.
 */
export default function MiniAppHomePage() {
  const locale = useLocale();
  const t = useTranslations('MiniApp.home');
  const tPlans = useTranslations('MiniApp.plans');
  const queryClient = useQueryClient();
  const { haptic, hapticNotification, colorScheme, webApp } = useTelegramWebApp();
  const { selectedSubscriptionKey } = useCustomerSubscriptions();
  const [inviteCode, setInviteCode] = useState('');
  const [inviteFeedback, setInviteFeedback] = useState<{ tone: 'success' | 'error'; message: string } | null>(null);
  const openedTracked = useRef(false);
  const loadedTracked = useRef(false);
  const failedTracked = useRef(false);
  const startParam = webApp?.initDataUnsafe?.start_param ?? null;

  const bootstrapQuery = useQuery({
    queryKey: ['miniapp-bootstrap', locale, startParam, selectedSubscriptionKey],
    queryFn: async () => {
      const { data } = await miniappApi.getBootstrap({
        locale,
        startParam,
        selectedSubscriptionKey,
      });
      return data;
    },
  });

  const bootstrap = bootstrapQuery.data;
  const hasActiveSubscription = bootstrap?.subscription.status === 'active';
  const isOnTrial = bootstrap?.subscription.status === 'trial';
  const rollout = bootstrap?.rollout;
  const canActivateTrial = Boolean(
    bootstrap?.trial.eligible
    && rollout?.enabled !== false
    && rollout?.accessGranted !== false
    && rollout?.trialEnabled !== false
    && rollout?.mode !== 'rollback'
    && rollout?.mode !== 'maintenance',
  );
  const rolloutBannerMessage = (() => {
    if (!rollout) return null;
    if (rollout.maintenanceMessage) return rollout.maintenanceMessage;
    if (rollout.mode === 'rollback') return t('rollbackDescription');
    if (rollout.mode === 'canary' && rollout.accessGranted === false) {
      return t('limitedRolloutDescription');
    }
    if (rollout.mode === 'maintenance' || rollout.enabled === false) {
      return t('serviceMaintenanceDescription');
    }
    return null;
  })();
  const usageData = bootstrap?.usage;
  const usageIsAvailable = usageData?.usageAvailable === true;
  const usagePercentage = usageIsAvailable && usageData?.bandwidthLimitBytes
    ? Math.round(
        (usageData.bandwidthUsedBytes / usageData.bandwidthLimitBytes) * 100,
      )
    : 0;
  const usageUnavailableLabel = translateOrFallback(t, 'usageUnavailable', 'Usage unavailable');
  const isLoading = bootstrapQuery.isLoading;
  const isSessionRestoring = bootstrapQuery.isError && !bootstrap;

  async function refreshMiniAppAccessState() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] }),
      queryClient.resetQueries({ queryKey: ['miniapp-config'], exact: true }),
      queryClient.invalidateQueries({ queryKey: ['miniapp-offers'] }),
      queryClient.invalidateQueries({ queryKey: ['usage'] }),
    ]);
  }

  const redeemInviteMutation = useMutation({
    mutationFn: async (code: string) => {
      const normalizedCode = code.trim().toUpperCase();
      const { data } = await invitesApi.redeem({ code: normalizedCode });
      return data;
    },
    onSuccess: async (data) => {
      hapticNotification('success');
      const reward = data.free_days
        ? tPlans('inviteRewardDays', { count: data.free_days })
        : tPlans('inviteRewardDefault');
      const message = tPlans('inviteRedeemed', { reward });
      setInviteFeedback({ tone: 'success', message });
      setInviteCode('');
      await refreshMiniAppAccessState();
      webApp?.showAlert(message);
    },
    onError: (error: unknown) => {
      hapticNotification('error');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const message = axiosError.response?.data?.detail || tPlans('inviteInvalid');
      setInviteFeedback({ tone: 'error', message });
      webApp?.showAlert(message);
    },
  });

  useEffect(() => {
    if (openedTracked.current) return;
    openedTracked.current = true;
    void emitMiniAppRuntimeEvent({
      event: 'miniapp_opened',
      page: 'home',
      locale,
      path: `/${locale}/miniapp/home`,
    });
  }, [locale]);

  useEffect(() => {
    if (!bootstrap || loadedTracked.current) return;
    loadedTracked.current = true;
    void emitMiniAppRuntimeEvent({
      event: 'miniapp_bootstrap_loaded',
      page: 'home',
      locale,
      path: `/${locale}/miniapp/home`,
      primaryCtaKind: bootstrap.primaryCta.kind,
      subscriptionStatus: bootstrap.subscription.status,
    });
  }, [bootstrap, locale]);

  useEffect(() => {
    if (!bootstrapQuery.isError || failedTracked.current) return;
    failedTracked.current = true;
    void emitMiniAppRuntimeEvent({
      event: 'miniapp_bootstrap_failed',
      page: 'home',
      locale,
      path: `/${locale}/miniapp/home`,
      errorCode: 'bootstrap_fetch_failed',
    });
  }, [bootstrapQuery.isError, locale]);

  const cardBg = 'miniapp-card';
  const borderColor = 'border';
  const accentColor = 'text-[var(--tg-link-color,var(--color-neon-cyan))]';

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-neon-cyan" role="status" />
          </div>
        ) : isSessionRestoring ? (
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-300" />
            <div>
              <h2 className="font-display text-base text-amber-100">{t('sessionRestoringTitle')}</h2>
              <p className="mt-1 text-xs font-mono text-amber-100/80">{t('sessionRestoringDescription')}</p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Shield
                  className={`h-6 w-6 ${hasActiveSubscription || isOnTrial ? accentColor : 'text-muted-foreground'}`}
                />
                <h2 className="text-lg font-display">
                  {hasActiveSubscription || isOnTrial ? t('subscriptionActive') : t('noSubscription')}
                </h2>
              </div>
              {isOnTrial && (
                <span className="text-xs font-mono px-2 py-1 rounded bg-neon-pink/20 text-neon-pink border border-neon-pink/30">
                  {t('trial')}
                </span>
              )}
            </div>

            {hasActiveSubscription && bootstrap && (
              <div className="space-y-2 text-sm font-mono text-muted-foreground">
                <div className="flex justify-between">
                  <span>{t('plan')}:</span>
                  <span className="text-foreground font-semibold">
                    {bootstrap.subscription.planName || translateOrFallback(t, 'defaultPlan', 'Premium')}
                  </span>
                </div>
                {bootstrap.subscription.expiresAt && (
                  <div className="flex justify-between">
                    <span>{t('expires')}:</span>
                    <span className="text-foreground">
                      {new Date(bootstrap.subscription.expiresAt).toLocaleDateString(locale)}
                    </span>
                  </div>
                )}
                {bootstrap.serviceState.providerName && (
                  <div className="flex justify-between">
                    <span>{t('provider')}:</span>
                    <span className="text-foreground">{bootstrap.serviceState.providerName}</span>
                  </div>
                )}
                {bootstrap.serviceState.channelType && (
                  <div className="flex justify-between">
                    <span>{t('channel')}:</span>
                    <span className="text-foreground">{bootstrap.serviceState.channelType}</span>
                  </div>
                )}
              </div>
            )}

            {!hasActiveSubscription && isOnTrial && bootstrap && (
              <div className="space-y-2 text-sm font-mono text-muted-foreground">
                <div className="flex justify-between">
                  <span>{t('plan')}:</span>
                  <span className="text-foreground">{t('trialPlan')}</span>
                </div>
                {bootstrap.trial.trialEnd && (
                  <div className="flex justify-between">
                    <span>{t('expires')}:</span>
                    <span className="text-foreground">
                      {new Date(bootstrap.trial.trialEnd).toLocaleDateString(locale)}
                    </span>
                  </div>
                )}
                {bootstrap.trial.daysRemaining > 0 && (
                  <div className="flex justify-between">
                    <span>{t('daysRemaining')}:</span>
                    <span className="text-neon-cyan font-semibold">{bootstrap.trial.daysRemaining}</span>
                  </div>
                )}
              </div>
            )}

            {!hasActiveSubscription && !isOnTrial && (
              <p className="text-sm text-muted-foreground font-mono">
                {t('noSubscriptionDescription')}
              </p>
            )}
          </>
        )}
      </motion.div>

      {rolloutBannerMessage ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-300" />
            <div>
              <h3 className="font-display text-sm text-amber-100">{t('serviceMaintenanceTitle')}</h3>
              <p className="mt-1 text-xs font-mono text-amber-100/80">{rolloutBannerMessage}</p>
            </div>
          </div>
        </motion.div>
      ) : null}

      {!hasActiveSubscription && !isOnTrial ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <div className="mb-3 flex items-center gap-2">
            <Users className="h-5 w-5 text-neon-purple" />
            <h3 className="font-display text-sm uppercase tracking-[0.14em]">
              {tPlans('haveInviteCode')}
            </h3>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={inviteCode}
              onChange={(event) => {
                setInviteCode(event.target.value.toUpperCase());
                if (inviteFeedback) {
                  setInviteFeedback(null);
                }
              }}
              placeholder={tPlans('inviteCodePlaceholder')}
              className="miniapp-input min-w-0 flex-1 rounded-xl border px-3 py-3 font-mono text-sm outline-none"
            />
            <button
              type="button"
              onClick={() => redeemInviteMutation.mutate(inviteCode)}
              disabled={!inviteCode.trim() || redeemInviteMutation.isPending}
              className="miniapp-purple-button rounded-xl px-4 py-3 font-mono text-sm disabled:opacity-50"
            >
              {redeemInviteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                tPlans('redeem')
              )}
            </button>
          </div>
          {inviteFeedback ? (
            <div
              className={`mt-3 flex items-center gap-2 text-xs font-mono ${
                inviteFeedback.tone === 'error' ? 'text-neon-pink' : 'text-neon-cyan'
              }`}
            >
              <Check className="h-3 w-3" />
              {inviteFeedback.message}
            </div>
          ) : null}
          <p className="mt-2 text-xs font-mono text-muted-foreground">
            {tPlans('inviteCodeNote')}
          </p>
        </motion.div>
      ) : null}

      {(hasActiveSubscription || isOnTrial) && usageData && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className={`h-5 w-5 ${accentColor}`} />
            <h3 className="font-display">{t('usage')}</h3>
          </div>

          {usageIsAvailable ? (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm font-mono mb-2">
                  <span className="text-muted-foreground">{t('dataUsed')}</span>
                  <span className="text-foreground">
                    {formatBytes(usageData.bandwidthUsedBytes)} /{' '}
                    {formatBytes(usageData.bandwidthLimitBytes)}
                  </span>
                </div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${usagePercentage}%` }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className={`h-full ${
                      usagePercentage >= 80 ? 'bg-destructive' : 'bg-neon-cyan'
                    }`}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-sm font-mono">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">{t('connections')}</span>
                </div>
                <span className="text-foreground">
                  {usageData.connectionsActive} / {usageData.connectionsLimit}
                </span>
              </div>

              {usageData.lastConnectionAt && (
                <div className="flex items-center justify-between text-sm font-mono">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">{t('lastConnected')}</span>
                  </div>
                  <span className="text-foreground">
                    {new Date(usageData.lastConnectionAt).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 font-mono text-sm text-amber-100">
              {usageUnavailableLabel}
            </div>
          )}
        </motion.div>
      )}

      {!hasActiveSubscription && !isOnTrial && canActivateTrial && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <div className="flex items-start gap-3">
            <Gift className="h-6 w-6 text-neon-pink flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-display mb-1">{t('trialAvailable')}</h3>
              <p className="text-sm text-muted-foreground font-mono mb-3">
                {t('trialDescription')}
              </p>
              <Link
                href="/miniapp/plans"
                onClick={() => haptic('medium')}
                className="inline-flex items-center gap-2 text-sm font-mono text-neon-pink hover:text-neon-pink/80 transition-colors"
              >
                {t('activateTrial')}
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      <VpnConfigCard colorScheme={colorScheme} page="home" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <h3 className="font-display text-sm text-muted-foreground mb-3">{t('quickActions')}</h3>
        <div className="grid grid-cols-2 gap-3">
          <QuickActionCard
            href="/miniapp/plans"
            icon={CreditCard}
            label={t('viewPlans')}
            onPress={() => haptic('medium')}
          />
          <QuickActionCard
            href="/miniapp/wallet"
            icon={Zap}
            label={t('wallet')}
            onPress={() => haptic('medium')}
          />
          <QuickActionCard
            href="/miniapp/profile"
            icon={Settings}
            label={t('settings')}
            onPress={() => haptic('medium')}
          />
          {(hasActiveSubscription || isOnTrial) && (
            <QuickActionCard
              href="/miniapp/profile#vpn-config"
              icon={Shield}
              label={t('vpnConfig')}
              onPress={() => haptic('medium')}
            />
          )}
        </div>
      </motion.div>
    </div>
  );
}

function QuickActionCard({
  href,
  icon: Icon,
  label,
  onPress,
}: {
  href: string;
  icon: typeof Shield;
  label: string;
  onPress: () => void;
}) {
  const cardBg = 'miniapp-card';
  const borderColor = 'border';

  return (
    <Link
      href={href}
      onClick={onPress}
      className={`${cardBg} ${borderColor} border rounded-lg p-4 flex flex-col items-center justify-center gap-2 text-center min-h-[100px] hover:border-neon-cyan/50 transition-colors touch-manipulation`}
    >
      <Icon className="h-6 w-6 text-[var(--tg-link-color,var(--color-neon-cyan))]" />
      <span className="text-sm font-mono">{label}</span>
    </Link>
  );
}
