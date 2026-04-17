'use client';

import { motion } from 'motion/react';
import { Check, Crown, Globe, ShieldCheck, Sparkles } from 'lucide-react';
import { useLocale } from 'next-intl';
import { cn } from '@/lib/utils';
import {
  formatConnectionModes,
  formatDurationLabel,
  formatSupportLabel,
  getMarketingBadge,
  getPlanHighlights,
  getPlanPrice,
  type SubscriptionPlan,
} from '../lib/plan-presenter';

interface PlanCardProps {
  plan: SubscriptionPlan;
  isCurrentPlan?: boolean;
  onPurchase: (planUuid: string) => void;
}

export function PlanCard({ plan, isCurrentPlan = false, onPurchase }: PlanCardProps) {
  const locale = useLocale();
  const price = getPlanPrice(plan, locale);
  const badge = getMarketingBadge(plan);
  const highlights = getPlanHighlights(plan).slice(0, 5);

  const tierConfig: Record<
    string,
    {
      icon: typeof Globe;
      border: string;
      glow: string;
      accent: string;
      badge: string;
      chip: string;
    }
  > = {
    basic: {
      icon: Globe,
      border: 'border-neon-cyan/40',
      glow: 'shadow-[0_20px_64px_-42px_rgba(0,255,255,0.55)]',
      accent: 'text-neon-cyan',
      badge: 'border-neon-cyan/40 text-neon-cyan',
      chip: 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30',
    },
    plus: {
      icon: Sparkles,
      border: 'border-matrix-green/45',
      glow: 'shadow-[0_24px_80px_-44px_rgba(0,255,136,0.6)]',
      accent: 'text-matrix-green',
      badge: 'border-matrix-green/40 text-matrix-green',
      chip: 'bg-matrix-green/10 text-matrix-green border-matrix-green/30',
    },
    pro: {
      icon: ShieldCheck,
      border: 'border-neon-pink/40',
      glow: 'shadow-[0_24px_80px_-44px_rgba(255,0,255,0.55)]',
      accent: 'text-neon-pink',
      badge: 'border-neon-pink/40 text-neon-pink',
      chip: 'bg-neon-pink/10 text-neon-pink border-neon-pink/30',
    },
    max: {
      icon: Crown,
      border: 'border-neon-purple/40',
      glow: 'shadow-[0_24px_80px_-44px_rgba(157,0,255,0.6)]',
      accent: 'text-neon-purple',
      badge: 'border-neon-purple/40 text-neon-purple',
      chip: 'bg-neon-purple/10 text-neon-purple border-neon-purple/30',
    },
  };

  const config = tierConfig[plan.plan_code] ?? tierConfig.basic;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className={cn(
        'relative overflow-hidden rounded-[1.75rem] border bg-black/45 p-6 backdrop-blur-2xl transition-all duration-300',
        isCurrentPlan
          ? 'border-matrix-green shadow-[0_0_24px_rgba(0,255,136,0.25)]'
          : `border-grid-line/30 hover:-translate-y-1 hover:${config.border}`,
        !isCurrentPlan && config.glow,
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.08),transparent_55%)] opacity-70" />

      {isCurrentPlan && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-matrix-green px-4 py-1 text-xs font-mono font-semibold text-terminal-bg">
          CURRENT PLAN
        </div>
      )}

      <div className="relative z-10">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={cn('rounded-2xl border bg-black/60 p-3', config.chip)}>
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-white/45">
                {plan.plan_code}
              </p>
              <h3 className="mt-1 text-2xl font-display text-white">
                {plan.display_name}
              </h3>
            </div>
          </div>
          {badge && (
            <span className={cn('rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em]', config.badge)}>
              {badge}
            </span>
          )}
        </div>

        <div className="mb-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="font-display text-4xl text-white">
                {price.formatted}
              </p>
              <p className="mt-2 font-mono text-xs uppercase tracking-[0.2em] text-white/45">
                per {formatDurationLabel(plan.duration_days)}
              </p>
            </div>
            <span className={cn('rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em]', config.chip)}>
              {formatSupportLabel(plan.support_sla)}
            </span>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">
              Devices
            </p>
            <p className="mt-2 text-lg font-display text-white">
              {plan.devices_included}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">
              Modes
            </p>
            <p className="mt-2 text-sm font-mono text-white/72">
              {formatConnectionModes(plan.connection_modes)}
            </p>
          </div>
        </div>

        <div className="mb-6 space-y-3 border-t border-white/10 pt-6">
          {highlights.map((feature) => (
            <div key={feature} className="flex items-start gap-3 text-sm font-mono text-white/76">
              <Check className={cn('mt-0.5 h-4 w-4 shrink-0', config.accent)} />
              <span>{feature}</span>
            </div>
          ))}
        </div>

        <button
          onClick={() => onPurchase(plan.uuid)}
          disabled={isCurrentPlan}
          className={cn(
            'w-full rounded-2xl border px-4 py-3 font-display text-sm uppercase tracking-[0.22em] transition-all duration-300',
            isCurrentPlan
              ? 'cursor-not-allowed border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
              : 'border-white/20 bg-white/[0.04] text-white hover:-translate-y-0.5 hover:bg-white hover:text-black',
          )}
        >
          {isCurrentPlan ? 'Current Plan' : 'Purchase'}
        </button>
      </div>

      {isCurrentPlan && (
        <>
          <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-matrix-green" aria-hidden="true" />
          <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-matrix-green" aria-hidden="true" />
          <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-matrix-green" aria-hidden="true" />
          <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-matrix-green" aria-hidden="true" />
        </>
      )}
    </motion.div>
  );
}
