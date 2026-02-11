'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { referralApi } from '@/lib/api';
import { motion } from 'motion/react';
import {
  Gift,
  Copy,
  Share2,
  QrCode,
  TrendingUp,
  Users,
  DollarSign,
  CheckCircle2,
  Loader2
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';
import QRCode from 'react-qr-code';

/**
 * Mini App Referral Program page
 * Dedicated page for referral code sharing, QR codes, stats, and commission history
 */
export default function MiniAppReferralPage() {
  const t = useTranslations('MiniApp.referral');
  const { haptic, colorScheme, webApp } = useTelegramWebApp();

  // Fetch referral data
  const { data: referralCode } = useQuery({
    queryKey: ['referral-code'],
    queryFn: async () => {
      const { data } = await referralApi.getCode();
      return data;
    },
  });

  const { data: referralStats } = useQuery({
    queryKey: ['referral-stats'],
    queryFn: async () => {
      const { data } = await referralApi.getStats();
      return data;
    },
  });

  const { data: referralStatus } = useQuery({
    queryKey: ['referral-status'],
    queryFn: async () => {
      const { data } = await referralApi.getStatus();
      return data;
    },
  });

  const { data: recentCommissions, isLoading: commissionsLoading } = useQuery({
    queryKey: ['referral-commissions'],
    queryFn: async () => {
      const { data } = await referralApi.getRecentCommissions();
      return data;
    },
  });

  const copyToClipboard = async (text: string) => {
    haptic('medium');
    try {
      await navigator.clipboard.writeText(text);
      webApp?.showAlert(t('copied'));
    } catch {
      webApp?.showAlert('Failed to copy');
    }
  };

  const shareReferralCode = () => {
    haptic('medium');
    if (referralCode?.referral_code) {
      const shareText = t('shareText', { code: referralCode.referral_code });
      webApp?.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(shareText)}`);
    }
  };

  // Theme colors
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  // Generate referral link for QR code
  const referralLink = referralCode?.referral_code
    ? `https://t.me/cybervpn_bot?start=${referralCode.referral_code}`
    : '';

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2"
      >
        <Gift className="h-6 w-6 text-neon-pink" />
        <h1 className="text-xl font-display">{t('title')}</h1>
      </motion.div>

      {/* Referral Code Card */}
      {referralCode && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <h2 className="text-sm font-display text-muted-foreground mb-3">{t('yourCode')}</h2>
          <div className="flex gap-2 mb-3">
            <div className="flex-1 px-4 py-3 bg-muted border border-border rounded-lg font-mono text-2xl text-center text-neon-cyan">
              {referralCode.referral_code}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => copyToClipboard(referralCode.referral_code)}
              className="py-2 px-4 bg-neon-cyan text-black rounded-lg hover:bg-neon-cyan/90 transition-colors touch-manipulation flex items-center justify-center gap-2 font-mono"
            >
              <Copy className="h-4 w-4" />
              Copy
            </button>
            <button
              onClick={shareReferralCode}
              className="py-2 px-4 bg-neon-purple text-white rounded-lg hover:bg-neon-purple/90 transition-colors touch-manipulation flex items-center justify-center gap-2 font-mono"
            >
              <Share2 className="h-4 w-4" />
              {t('shareCode')}
            </button>
          </div>
        </motion.div>
      )}

      {/* QR Code Card */}
      {referralLink && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-4`}
        >
          <div className="flex items-center gap-2 mb-3">
            <QrCode className="h-5 w-5 text-neon-cyan" />
            <h2 className="text-sm font-display">{t('qrCodeTitle')}</h2>
          </div>
          <div className="flex justify-center p-4 bg-white rounded-lg">
            <QRCode
              value={referralLink}
              size={200}
              level="M"
              fgColor="#000000"
              bgColor="#FFFFFF"
            />
          </div>
          <p className="text-xs text-muted-foreground text-center mt-3 font-mono">
            {t('scanToJoin')}
          </p>
        </motion.div>
      )}

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="space-y-2"
      >
        <h2 className="text-sm font-display text-muted-foreground">{t('stats')}</h2>
        <div className="grid grid-cols-3 gap-2">
          <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
            <div className="flex items-center gap-1 mb-2">
              <Users className="h-4 w-4 text-neon-cyan" />
            </div>
            <div className="text-2xl font-display text-neon-cyan">
              {referralStats?.total_referrals || 0}
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {t('totalReferrals')}
            </div>
          </div>

          <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
            <div className="flex items-center gap-1 mb-2">
              <DollarSign className="h-4 w-4 text-neon-cyan" />
            </div>
            <div className="text-2xl font-display text-neon-cyan">
              ${(referralStats?.total_earned || 0).toFixed(2)}
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {t('totalEarned')}
            </div>
          </div>

          <div className={`${cardBg} ${borderColor} border rounded-lg p-3`}>
            <div className="flex items-center gap-1 mb-2">
              <TrendingUp className="h-4 w-4 text-neon-cyan" />
            </div>
            <div className="text-2xl font-display text-neon-cyan">
              {referralStatus?.commission_rate ? `${referralStatus.commission_rate}%` : '-'}
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {t('referralRate')}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Recent Commissions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <h2 className="text-sm font-display mb-3">{t('recentCommissions')}</h2>
        {commissionsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-neon-cyan" />
          </div>
        ) : recentCommissions && Array.isArray(recentCommissions) && recentCommissions.length > 0 ? (
          <div className="space-y-2">
            {recentCommissions.map((commission: {
              id?: string;
              amount?: number;
              created_at?: string;
              user_login?: string;
            }, index: number) => (
              <div
                key={commission.id || index}
                className="flex items-center justify-between p-3 bg-muted rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-neon-cyan" />
                  <div>
                    <div className="text-sm font-mono text-neon-cyan">
                      ${(commission.amount || 0).toFixed(2)}
                    </div>
                    {commission.user_login && (
                      <div className="text-xs text-muted-foreground font-mono">
                        {t('commissionFrom')}: {commission.user_login}
                      </div>
                    )}
                  </div>
                </div>
                {commission.created_at && (
                  <div className="text-xs text-muted-foreground font-mono">
                    {new Date(commission.created_at).toLocaleDateString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4 font-mono">
            {t('noCommissions')}
          </p>
        )}
      </motion.div>

      {/* How It Works */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-4`}
      >
        <h2 className="text-sm font-display mb-3">{t('howItWorks')}</h2>
        <div className="space-y-3">
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-neon-cyan/20 flex items-center justify-center text-xs font-display text-neon-cyan">
              1
            </div>
            <p className="text-sm text-muted-foreground font-mono">{t('step1')}</p>
          </div>
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-neon-cyan/20 flex items-center justify-center text-xs font-display text-neon-cyan">
              2
            </div>
            <p className="text-sm text-muted-foreground font-mono">{t('step2')}</p>
          </div>
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-neon-cyan/20 flex items-center justify-center text-xs font-display text-neon-cyan">
              3
            </div>
            <p className="text-sm text-muted-foreground font-mono">{t('step3')}</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
