'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useReferralCode, useReferralStats, useRecentCommissions } from '../hooks/useReferral';
import { Copy, Check, Users, DollarSign, Percent, TrendingUp } from 'lucide-react';

interface Commission {
  id: string;
  description?: string;
  created_at: string;
  amount?: number;
}

export function ReferralClient() {
  const t = useTranslations('Referral');
  const [copied, setCopied] = useState(false);

  const { data: codeData, isLoading: codeLoading } = useReferralCode();
  const { data: stats, isLoading: statsLoading } = useReferralStats();
  const { data: commissionsData, isLoading: commissionsLoading } = useRecentCommissions();

  const referralCode = codeData?.referral_code;
  const commissions = commissionsData || [];

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  const copyReferralCode = () => {
    if (referralCode) {
      navigator.clipboard.writeText(referralCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Referral Code Card */}
      <div className="cyber-card p-8">
        <div className="flex items-center gap-3 mb-6">
          <Users className="h-8 w-8 text-neon-purple" />
          <h2 className="text-2xl font-display text-neon-purple">{t('yourCode') || 'Your Referral Code'}</h2>
        </div>

        {codeLoading ? (
          <div className="h-16 bg-grid-line/20 rounded animate-pulse" />
        ) : (
          <div className="flex items-center gap-4">
            <div className="flex-1 bg-terminal-surface border border-grid-line/30 rounded px-6 py-4 font-mono text-2xl text-neon-cyan tracking-wider">
              {referralCode || 'N/A'}
            </div>
            <button
              onClick={copyReferralCode}
              className="px-6 py-4 bg-neon-purple/20 hover:bg-neon-purple/30 border border-neon-purple/50 text-neon-purple font-mono text-sm rounded transition-colors flex items-center gap-2"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4" />
                  {t('copied') || 'Copied!'}
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  {t('copy') || 'Copy'}
                </>
              )}
            </button>
          </div>
        )}

        <p className="text-sm text-muted-foreground font-mono mt-4">
          {t('shareDescription') || 'Share this code with friends to earn commissions on their subscriptions'}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Total Referrals */}
        <div className="cyber-card p-6">
          <div className="flex items-center gap-3 mb-3">
            <Users className="h-5 w-5 text-neon-cyan" />
            <h3 className="text-sm font-mono text-muted-foreground uppercase">{t('totalReferrals') || 'Total Referrals'}</h3>
          </div>
          {statsLoading ? (
            <div className="h-10 bg-grid-line/20 rounded animate-pulse" />
          ) : (
            <div className="text-3xl font-display text-neon-cyan">
              {stats?.total_referrals || 0}
            </div>
          )}
        </div>

        {/* Total Earnings */}
        <div className="cyber-card p-6">
          <div className="flex items-center gap-3 mb-3">
            <DollarSign className="h-5 w-5 text-matrix-green" />
            <h3 className="text-sm font-mono text-muted-foreground uppercase">{t('totalEarnings') || 'Total Earnings'}</h3>
          </div>
          {statsLoading ? (
            <div className="h-10 bg-grid-line/20 rounded animate-pulse" />
          ) : (
            <div className="text-3xl font-display text-matrix-green">
              {formatCurrency(stats?.total_earned || 0)}
            </div>
          )}
        </div>

        {/* Commission Rate */}
        <div className="cyber-card p-6">
          <div className="flex items-center gap-3 mb-3">
            <Percent className="h-5 w-5 text-neon-purple" />
            <h3 className="text-sm font-mono text-muted-foreground uppercase">{t('commissionRate') || 'Commission Rate'}</h3>
          </div>
          {statsLoading ? (
            <div className="h-10 bg-grid-line/20 rounded animate-pulse" />
          ) : (
            <div className="text-3xl font-display text-neon-purple">
              {stats?.commission_rate || 0}%
            </div>
          )}
        </div>
      </div>

      {/* Recent Commissions */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple flex items-center gap-3">
          <TrendingUp className="h-5 w-5" />
          {t('recentCommissions') || 'Recent Commissions'}
        </h2>

        {commissionsLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="cyber-card p-4 animate-pulse">
                <div className="h-4 bg-grid-line/20 rounded w-3/4 mb-2" />
                <div className="h-3 bg-grid-line/20 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : commissions.length === 0 ? (
          <div className="cyber-card p-8 text-center">
            <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-muted-foreground font-mono">{t('noCommissions') || 'No commissions yet'}</p>
            <p className="text-sm text-muted-foreground font-mono mt-2">
              {t('startReferring') || 'Start referring friends to earn commissions!'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {commissions.map((commission: Commission) => (
              <div
                key={commission.id}
                className="cyber-card p-4 flex items-center justify-between hover:bg-terminal-surface/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <TrendingUp className="h-5 w-5 text-matrix-green" />
                  <div>
                    <p className="font-mono text-sm">
                      {commission.description || `Referral commission`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(commission.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="font-display text-lg text-matrix-green">
                  +{formatCurrency(commission.amount || 0)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
