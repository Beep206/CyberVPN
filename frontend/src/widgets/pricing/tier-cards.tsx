'use client';

import { motion } from 'motion/react';
import { useLocale, useTranslations } from 'next-intl';
import { Check, Crown, Orbit, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from '@/i18n/navigation';
import { TierLevel } from './pricing-dashboard';
import { cn } from '@/lib/utils';
import type { PricingPlanFamily, PricingTierCode } from './types';
import { formatMoney, getPlanPeriod, getPreferredCurrency } from './utils';

interface TierCardsProps {
  hoveredTier: TierLevel;
  onHover: (tier: TierLevel) => void;
  plans: PricingPlanFamily[];
  selectedPeriod: number;
}

const tierConfig: Record<
  PricingTierCode,
  {
    icon: typeof Orbit;
    color: string;
    border: string;
    glow: string;
    bgHover: string;
  }
> = {
  basic: {
    icon: Orbit,
    color: '#00ffff',
    border: 'border-neon-cyan/30',
    glow: 'shadow-[0_24px_80px_-48px_rgba(0,255,255,0.6)]',
    bgHover: 'hover:bg-neon-cyan/5',
  },
  plus: {
    icon: Sparkles,
    color: '#00ff88',
    border: 'border-matrix-green/40',
    glow: 'shadow-[0_24px_80px_-48px_rgba(0,255,136,0.55)]',
    bgHover: 'hover:bg-matrix-green/10',
  },
  pro: {
    icon: ShieldCheck,
    color: '#ff00ff',
    border: 'border-neon-pink/40',
    glow: 'shadow-[0_24px_80px_-48px_rgba(255,0,255,0.5)]',
    bgHover: 'hover:bg-neon-pink/10',
  },
  max: {
    icon: Crown,
    color: '#9d00ff',
    border: 'border-neon-purple/40',
    glow: 'shadow-[0_24px_80px_-48px_rgba(157,0,255,0.55)]',
    bgHover: 'hover:bg-neon-purple/10',
  },
};

export function TierCards({ hoveredTier, onHover, plans, selectedPeriod }: TierCardsProps) {
  const t = useTranslations('Pricing');
  const locale = useLocale();

  return (
    <div className="grid max-w-7xl grid-cols-1 gap-6 px-4 md:grid-cols-2 xl:grid-cols-4">
      {plans.map((plan, index) => {
        const config = tierConfig[plan.code];
        const Icon = config.icon;
        const isHovered = hoveredTier === plan.code;
        const activePeriod = getPlanPeriod(plan, selectedPeriod);
        const preferredPrice = getPreferredCurrency(locale, activePeriod);
        const monthlyEquivalent = preferredPrice.amount / Math.max(activePeriod.duration_days / 30, 1);
        const modeLabel = plan.connection_modes
          .map((mode) => t(`modeNames.${mode}`))
          .join(' · ');
        const poolLabel = plan.server_pool
          .map((pool) => t(`poolNames.${pool}`))
          .join(' · ');
        const inviteLabel = activePeriod.invite_bundle.count > 0
          ? t('labels.inviteBundle', {
              count: activePeriod.invite_bundle.count,
              days: activePeriod.invite_bundle.friend_days,
            })
          : t('labels.inviteNone');
        const dedicatedIpLabel = plan.dedicated_ip.included > 0
          ? t('labels.includedDedicatedIp', { count: plan.dedicated_ip.included })
          : t('labels.dedicatedIpAddon');
        const badge =
          typeof plan.features.marketing_badge === 'string'
            ? String(plan.features.marketing_badge)
            : t(`tiers.${plan.code}.badge`);

        const bulletRows = [
          t('labels.devices', { count: plan.devices_included }),
          t('labels.unlimitedFairUse'),
          modeLabel,
          poolLabel,
          dedicatedIpLabel,
          inviteLabel,
        ];

        return (
          <motion.article
            key={plan.code}
            initial={{ opacity: 0, y: 48 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.12, type: 'spring', damping: 22, stiffness: 120 }}
            onMouseEnter={() => onHover(plan.code)}
            onMouseLeave={() => onHover('plus')}
            className={cn(
              'group relative flex min-h-[38rem] flex-col overflow-hidden rounded-[2rem] border bg-black/45 p-7 backdrop-blur-2xl transition-all duration-500',
              config.border,
              config.bgHover,
              isHovered ? `-translate-y-3 scale-[1.01] ${config.glow}` : 'translate-y-0',
              plan.code === 'plus' && !isHovered && config.glow,
            )}
            style={{
              borderColor: isHovered ? config.color : undefined,
            }}
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
              style={{
                background: `radial-gradient(circle at top right, ${config.color}33, transparent 58%)`,
              }}
            />
            <div className="pointer-events-none absolute inset-x-7 top-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent" />
            <div className="relative z-10 flex flex-1 flex-col">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div
                    className="rounded-2xl border bg-black/55 p-3 transition-colors duration-300"
                    style={{ borderColor: `${config.color}66` }}
                  >
                    <Icon className="h-6 w-6" style={{ color: config.color }} />
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-white/45">
                      {t(`tiers.${plan.code}.eyebrow`)}
                    </p>
                    <h3 className="mt-1 font-display text-2xl font-bold uppercase tracking-[0.18em] text-white">
                      {plan.display_name}
                    </h3>
                  </div>
                </div>
                {badge ? (
                  <span
                    className="rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.24em]"
                    style={{
                      borderColor: `${config.color}66`,
                      color: config.color,
                    }}
                  >
                    {badge}
                  </span>
                ) : null}
              </div>

              <div className="mb-6">
                <div className="flex items-end gap-3">
                  <span className="font-display text-5xl font-black tracking-tight text-white">
                    {formatMoney(locale, preferredPrice.amount, preferredPrice.currency)}
                  </span>
                  <span className="pb-2 font-mono text-[11px] uppercase tracking-[0.24em] text-white/45">
                    {t('labels.perSelectedTerm', { days: activePeriod.duration_days })}
                  </span>
                </div>
                <p className="mt-2 font-mono text-xs uppercase tracking-[0.18em] text-white/55">
                  {t('labels.monthlyEquivalent', {
                    price: formatMoney(locale, monthlyEquivalent, preferredPrice.currency),
                  })}
                </p>
                <p className="mt-4 min-h-[4.25rem] text-sm font-mono leading-relaxed text-white/72">
                  {t(`tiers.${plan.code}.description`)}
                </p>
              </div>

              <div className="mb-6 flex flex-wrap gap-2">
                <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/60">
                  {t(`tiers.${plan.code}.audience`)}
                </span>
                <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/60">
                  {t(`supportNames.${plan.support_sla}`)}
                </span>
              </div>

              <div className="flex-1">
                <ul className="space-y-3">
                  {bulletRows.map((feature, featureIndex) => (
                    <motion.li
                      key={`${plan.code}-${featureIndex}`}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.08 + featureIndex * 0.04 }}
                      className="flex items-start gap-3 text-sm font-mono text-white/78"
                    >
                      <Check className="mt-0.5 h-4 w-4 shrink-0" style={{ color: config.color }} />
                      <span>{feature}</span>
                    </motion.li>
                  ))}
                </ul>
              </div>

              <div className="mt-8 grid gap-3">
                <div className="rounded-2xl border border-white/10 bg-black/40 px-4 py-3">
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
                    {t('summary.selectedTerm', { days: activePeriod.duration_days })}
                  </p>
                  <p className="mt-1 text-sm font-mono text-white/75">
                    {activePeriod.invite_bundle.count > 0 ? inviteLabel : t('summary.noInviteBonus')}
                  </p>
                </div>

                <Link
                  href="/register"
                  className="inline-flex h-14 items-center justify-center rounded-2xl border bg-black px-6 text-center font-display text-sm font-bold uppercase tracking-[0.24em] text-white transition-all duration-300 hover:-translate-y-0.5 hover:bg-white hover:text-black"
                  style={{ borderColor: config.color }}
                >
                  {t(`tiers.${plan.code}.button`)}
                </Link>
              </div>
            </div>
          </motion.article>
        );
      })}
    </div>
  );
}
