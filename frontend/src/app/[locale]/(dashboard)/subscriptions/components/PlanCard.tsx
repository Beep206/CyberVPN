'use client';

import { motion } from 'motion/react';
import { Check, Zap, Shield, Globe } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface Plan {
  uuid: string;
  name: string;
  price: number;
  currency: string;
  durationDays: number;
  dataLimitGb?: number | null;
  maxDevices?: number | null;
  features?: string[] | null;
  isActive: boolean;
}

interface PlanCardProps {
  plan: Plan;
  isCurrentPlan?: boolean;
  onPurchase: (planUuid: string) => void;
}

export function PlanCard({ plan, isCurrentPlan = false, onPurchase }: PlanCardProps) {
  const t = useTranslations('Subscriptions');

  // Format duration
  const formatDuration = (days: number): string => {
    if (days === 1) return '1 day';
    if (days === 7) return '1 week';
    if (days === 30 || days === 31) return '1 month';
    if (days === 90) return '3 months';
    if (days === 180) return '6 months';
    if (days === 365 || days === 366) return '1 year';
    return `${days} days`;
  };

  // Format traffic
  const formatTraffic = (gb: number | null | undefined): string => {
    if (!gb) return 'Unlimited';
    if (gb >= 1000) return `${gb / 1000} TB`;
    return `${gb} GB`;
  };

  // Icon for plan type (simple heuristic based on price)
  const getPlanIcon = () => {
    if (plan.price === 0) return Shield;
    if (plan.price < 10) return Globe;
    return Zap;
  };

  const Icon = getPlanIcon();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className={`relative cyber-card p-6 transition-all duration-300 ${
        isCurrentPlan
          ? 'border-matrix-green shadow-[0_0_20px_rgba(0,255,136,0.3)]'
          : 'border-grid-line/30 hover:border-neon-cyan/50'
      }`}
    >
      {/* Current Plan Badge */}
      {isCurrentPlan && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-matrix-green text-terminal-bg text-xs font-mono font-semibold rounded-full">
          CURRENT PLAN
        </div>
      )}

      {/* Header */}
      <div className="text-center mb-6">
        <div className="inline-block p-3 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg mb-3">
          <Icon className="h-8 w-8 text-neon-cyan" />
        </div>
        <h3 className="text-2xl font-display text-neon-cyan mb-2">
          {plan.name}
        </h3>
        <div className="flex items-baseline justify-center gap-2">
          <span className="text-4xl font-display text-foreground">
            {plan.price}
          </span>
          <span className="text-lg text-muted-foreground font-mono">
            {plan.currency}
          </span>
        </div>
        <p className="text-sm text-muted-foreground font-mono mt-1">
          {formatDuration(plan.durationDays)}
        </p>
      </div>

      {/* Stats */}
      <div className="space-y-3 mb-6 pb-6 border-b border-grid-line/30">
        <div className="flex justify-between items-center text-sm">
          <span className="text-muted-foreground">Traffic</span>
          <span className="font-mono text-neon-cyan">
            {formatTraffic(plan.dataLimitGb)}
          </span>
        </div>
        {plan.maxDevices && (
          <div className="flex justify-between items-center text-sm">
            <span className="text-muted-foreground">Devices</span>
            <span className="font-mono text-neon-cyan">
              {plan.maxDevices}
            </span>
          </div>
        )}
      </div>

      {/* Features */}
      {plan.features && plan.features.length > 0 && (
        <div className="space-y-2 mb-6">
          {plan.features.map((feature, index) => (
            <div key={index} className="flex items-start gap-2">
              <Check className="h-4 w-4 text-matrix-green flex-shrink-0 mt-0.5" />
              <span className="text-sm text-muted-foreground">{feature}</span>
            </div>
          ))}
        </div>
      )}

      {/* Action Button */}
      <button
        onClick={() => onPurchase(plan.uuid)}
        disabled={isCurrentPlan}
        className={`w-full px-4 py-3 font-mono text-sm rounded transition-all duration-300 ${
          isCurrentPlan
            ? 'bg-matrix-green/10 border border-matrix-green/30 text-matrix-green cursor-not-allowed'
            : 'bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]'
        }`}
      >
        {isCurrentPlan ? 'Active' : 'Purchase'}
      </button>

      {/* Decorative corners */}
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
