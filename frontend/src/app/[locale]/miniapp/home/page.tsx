'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { entitlementsApi, serviceAccessApi, trialApi, vpnApi } from '@/lib/api';
import { motion } from 'motion/react';
import {
  Shield,
  Zap,
  CreditCard,
  Settings,
  TrendingUp,
  Clock,
  Server,
  Gift,
  ExternalLink
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import { Link } from '@/i18n/navigation';
import { VpnConfigCard } from '../components/VpnConfigCard';
// import { useAuthStore } from '@/stores/auth-store'; // TODO: Use when subscription data available

/**
 * Mini App Home/Dashboard page
 * Shows subscription status, usage stats, trial info, and quick actions
 */
export default function MiniAppHomePage() {
  const t = useTranslations('MiniApp.home');
  const { haptic, colorScheme, webApp } = useTelegramWebApp();
  // const user = useAuthStore((s) => s.user); // TODO: Use for subscription info when available

  // Fetch usage stats
  const { data: usageData, isLoading: usageLoading } = useQuery({
    queryKey: ['usage'],
    queryFn: async () => {
      const { data } = await vpnApi.getUsage();
      return data;
    },
  });

  // Fetch trial status
  const { data: trialData, isLoading: trialLoading } = useQuery({
    queryKey: ['trial'],
    queryFn: async () => {
      const { data } = await trialApi.getStatus();
      return data;
    },
  });

  const { data: entitlementData, isLoading: entitlementsLoading } = useQuery({
    queryKey: ['miniapp-current-entitlements'],
    queryFn: async () => {
      const { data } = await entitlementsApi.getCurrent();
      return data;
    },
  });

  const telegramUserId = webApp?.initDataUnsafe.user?.id ?? null;
  const { data: currentServiceState, isLoading: serviceStateLoading } = useQuery({
    queryKey: ['miniapp-current-service-state', telegramUserId],
    queryFn: async () => {
      const { data } = await serviceAccessApi.getCurrentServiceState({
        provider_name: 'remnawave',
        channel_type: 'telegram_bot',
        credential_type: 'telegram_bot',
        credential_subject_key: telegramUserId ? `telegram-miniapp:${telegramUserId}` : 'telegram-miniapp',
      });
      return data;
    },
    enabled: telegramUserId !== null,
  });

  const hasActiveSubscription = entitlementData?.status === 'active';
  const isOnTrial = Boolean(entitlementData?.is_trial || trialData?.is_trial_active);
  const canActivateTrial = Boolean(trialData?.eligible || trialData?.is_eligible);

  // Format usage percentage
  const usagePercentage = usageData?.bandwidth_limit_bytes
    ? Math.round((usageData.bandwidth_used_bytes / usageData.bandwidth_limit_bytes) * 100)
    : 0;

  // Format bytes to GB
  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return '0 GB';
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
  };

  const isLoading = usageLoading || trialLoading || entitlementsLoading || serviceStateLoading;

  // Theme colors
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';
  const accentColor = 'text-[var(--tg-link-color,var(--color-neon-cyan))]';

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      {/* Subscription Status Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-neon-cyan" />
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Shield className={`h-6 w-6 ${hasActiveSubscription || isOnTrial ? accentColor : 'text-muted-foreground'}`} />
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

            {/* Active Subscription Info */}
            {hasActiveSubscription && entitlementData && (
              <div className="space-y-2 text-sm font-mono text-muted-foreground">
                <div className="flex justify-between">
                  <span>{t('plan')}:</span>
                  <span className="text-foreground font-semibold">
                    {entitlementData.display_name || entitlementData.plan_code || 'Premium'}
                  </span>
                </div>
                {entitlementData.expires_at && (
                  <div className="flex justify-between">
                    <span>{t('expires')}:</span>
                    <span className="text-foreground">
                      {new Date(entitlementData.expires_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
                {currentServiceState?.provider_name && (
                  <div className="flex justify-between">
                    <span>Provider:</span>
                    <span className="text-foreground">{currentServiceState.provider_name}</span>
                  </div>
                )}
                {currentServiceState?.consumption_context?.channel_type && (
                  <div className="flex justify-between">
                    <span>Channel:</span>
                    <span className="text-foreground">{currentServiceState.consumption_context.channel_type}</span>
                  </div>
                )}
              </div>
            )}

            {/* Trial Info */}
            {!hasActiveSubscription && isOnTrial && trialData && (
              <div className="space-y-2 text-sm font-mono text-muted-foreground">
                <div className="flex justify-between">
                  <span>{t('plan')}:</span>
                  <span className="text-foreground">{t('trialPlan')}</span>
                </div>
                {trialData.trial_end && (
                  <div className="flex justify-between">
                    <span>{t('expires')}:</span>
                    <span className="text-foreground">
                      {new Date(trialData.trial_end).toLocaleDateString()}
                    </span>
                  </div>
                )}
                {trialData.days_remaining > 0 && (
                  <div className="flex justify-between">
                    <span>{t('daysRemaining')}:</span>
                    <span className="text-neon-cyan font-semibold">
                      {trialData.days_remaining}
                    </span>
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

      {/* Usage Stats */}
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

          <div className="space-y-4">
            {/* Data usage */}
            <div>
              <div className="flex justify-between text-sm font-mono mb-2">
                <span className="text-muted-foreground">{t('dataUsed')}</span>
                <span className="text-foreground">
                  {formatBytes(usageData.bandwidth_used_bytes)} / {formatBytes(usageData.bandwidth_limit_bytes)}
                </span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${usagePercentage}%` }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  className={`h-full ${usagePercentage > 80 ? 'bg-destructive' : 'bg-neon-cyan'}`}
                />
              </div>
            </div>

            {/* Connections */}
            <div className="flex items-center justify-between text-sm font-mono">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">{t('connections')}</span>
              </div>
              <span className="text-foreground">
                {usageData.connections_active} / {usageData.connections_limit}
              </span>
            </div>

            {/* Last connected */}
            {usageData.last_connection_at && (
              <div className="flex items-center justify-between text-sm font-mono">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">{t('lastConnected')}</span>
                </div>
                <span className="text-foreground">
                  {new Date(usageData.last_connection_at).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Trial Section */}
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

      {/* VPN Config Card */}
      <VpnConfigCard colorScheme={colorScheme} />

      {/* Quick Actions Grid */}
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
            colorScheme={colorScheme}
            onPress={() => haptic('medium')}
          />
          <QuickActionCard
            href="/miniapp/wallet"
            icon={Zap}
            label={t('wallet')}
            colorScheme={colorScheme}
            onPress={() => haptic('medium')}
          />
          <QuickActionCard
            href="/miniapp/profile"
            icon={Settings}
            label={t('settings')}
            colorScheme={colorScheme}
            onPress={() => haptic('medium')}
          />
          {(hasActiveSubscription || isOnTrial) && (
            <QuickActionCard
              href="/profile#vpn-config"
              icon={Shield}
              label={t('vpnConfig')}
              colorScheme={colorScheme}
              onPress={() => haptic('medium')}
            />
          )}
        </div>
      </motion.div>
    </div>
  );
}

// Quick Action Card Component
function QuickActionCard({
  href,
  icon: Icon,
  label,
  colorScheme,
  onPress,
}: {
  href: string;
  icon: typeof Shield;
  label: string;
  colorScheme: 'light' | 'dark';
  onPress: () => void;
}) {
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

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
