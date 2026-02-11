'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { trialApi } from '@/lib/api/trial';
import { motion } from 'motion/react';
import { Zap, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { AxiosError } from 'axios';

export function TrialSection() {
  const t = useTranslations('Subscriptions');

  const [activating, setActivating] = useState(false);
  const [error, setError] = useState('');

  // Fetch trial status
  const { data: trialStatus, isLoading, refetch } = useQuery({
    queryKey: ['trial-status'],
    queryFn: async () => {
      const response = await trialApi.getStatus();
      return response.data;
    },
    staleTime: 1 * 60 * 1000, // Consider data fresh for 1 minute
  });

  // Handle trial activation
  const handleActivate = async () => {
    setActivating(true);
    setError('');

    try {
      await trialApi.activate();
      await refetch();
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 400) {
          setError(detail || 'You are not eligible for a trial');
        } else if (err.response?.status === 409) {
          setError('Trial already activated');
        } else {
          setError(detail || 'Failed to activate trial');
        }
      } else {
        setError('An error occurred. Please try again.');
      }
    } finally {
      setActivating(false);
    }
  };

  // Calculate days remaining (use state to avoid hydration mismatch)
  const [now] = useState(() => new Date());

  const getDaysRemaining = (trialEnd: string): number => {
    const end = new Date(trialEnd);
    const diff = end.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  if (isLoading) {
    return (
      <div className="cyber-card p-6 animate-pulse">
        <div className="h-6 bg-grid-line/30 rounded w-1/3 mb-4" />
        <div className="h-4 bg-grid-line/20 rounded w-2/3" />
      </div>
    );
  }

  // Don't show section if not eligible and not active
  if (!trialStatus?.is_eligible && !trialStatus?.is_active) {
    return null;
  }

  // Active trial - show badge
  if (trialStatus?.is_active && trialStatus?.trial_end) {
    const daysRemaining = getDaysRemaining(trialStatus.trial_end);
    const isExpiringSoon = daysRemaining <= 2;

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`cyber-card p-6 ${
          isExpiringSoon
            ? 'border-yellow-500/50 shadow-[0_0_20px_rgba(234,179,8,0.2)]'
            : 'border-neon-purple/50 shadow-[0_0_20px_rgba(168,85,247,0.2)]'
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4 flex-1">
            <div className={`p-3 rounded-lg ${
              isExpiringSoon
                ? 'bg-yellow-500/10 border border-yellow-500/30'
                : 'bg-neon-purple/10 border border-neon-purple/30'
            }`}>
              {isExpiringSoon ? (
                <Clock className="h-6 w-6 text-yellow-500" />
              ) : (
                <Zap className="h-6 w-6 text-neon-purple" />
              )}
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-display text-neon-purple">
                  Free Trial Active
                </h3>
                <span className={`px-2 py-1 rounded text-xs font-mono ${
                  isExpiringSoon
                    ? 'bg-yellow-500/20 text-yellow-500'
                    : 'bg-matrix-green/20 text-matrix-green'
                }`}>
                  {daysRemaining} {daysRemaining === 1 ? 'day' : 'days'} remaining
                </span>
              </div>

              <p className="text-sm text-muted-foreground mb-3">
                {isExpiringSoon
                  ? 'Your trial is expiring soon. Choose a plan to continue access.'
                  : 'Enjoy full access to all premium features during your trial period.'}
              </p>

              <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
                <Clock className="h-3 w-3" />
                <span>
                  Expires: {new Date(trialStatus.trial_end).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  // Eligible for trial - show activation button
  if (trialStatus?.is_eligible) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="cyber-card p-6 border-matrix-green/50 shadow-[0_0_20px_rgba(0,255,136,0.2)]"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4 flex-1">
            <div className="p-3 bg-matrix-green/10 border border-matrix-green/30 rounded-lg">
              <Zap className="h-6 w-6 text-matrix-green" />
            </div>

            <div className="flex-1">
              <h3 className="text-lg font-display text-matrix-green mb-1">
                Try CyberVPN Free for 7 Days
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Get full access to all premium features with no payment required. Cancel anytime.
              </p>

              {/* Features List */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
                {[
                  'Unlimited bandwidth',
                  'All server locations',
                  'Multi-device support',
                  'Premium protocols',
                ].map((feature, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                    <CheckCircle className="h-3 w-3 text-matrix-green" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              {/* Error Message */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded text-red-500 text-sm font-mono mb-4"
                >
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}

              {/* Activation Button */}
              <button
                onClick={handleActivate}
                disabled={activating}
                className="px-6 py-3 bg-matrix-green/20 hover:bg-matrix-green/30 border border-matrix-green/50 text-matrix-green font-mono text-sm rounded transition-all duration-300 hover:shadow-[0_0_15px_rgba(0,255,136,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {activating ? 'Activating...' : 'Start Free Trial'}
              </button>

              <p className="text-xs text-muted-foreground mt-3 font-mono">
                No credit card required · Cancel anytime
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  return null;
}
