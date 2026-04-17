'use client';

import { motion } from 'motion/react';
import { useLocale, useTranslations } from 'next-intl';
import { Check, Dot, Minus, PlugZap } from 'lucide-react';
import { MobileDataList } from '@/shared/ui/mobile-data-list';
import type { PricingAddon, PricingPlanFamily, PricingTierCode } from './types';
import { formatMoney, formatPlanLimitSummary, getPlanPeriod, getPreferredCurrency } from './utils';

const PLAN_ORDER: PricingTierCode[] = ['basic', 'plus', 'pro', 'max'];
const PLAN_TEXT_STYLES: Record<PricingTierCode, string> = {
  basic: 'text-neon-cyan',
  plus: 'text-matrix-green',
  pro: 'text-neon-pink',
  max: 'text-neon-purple',
};

function renderValue(value: boolean | string, accentClassName: string) {
  if (typeof value === 'boolean') {
    return value ? (
      <Check className={`h-5 w-5 ${accentClassName}`} />
    ) : (
      <Minus className="h-5 w-5 text-white/20" />
    );
  }

  return <span className={accentClassName}>{value}</span>;
}

function formatModes(
  t: ReturnType<typeof useTranslations>,
  plan: PricingPlanFamily,
) {
  return plan.connection_modes.map((mode) => t(`modeNames.${mode}`)).join(' · ');
}

function formatServerPool(
  t: ReturnType<typeof useTranslations>,
  plan: PricingPlanFamily,
) {
  return plan.server_pool.map((pool) => t(`poolNames.${pool}`)).join(' · ');
}

function formatDedicatedIp(
  t: ReturnType<typeof useTranslations>,
  plan: PricingPlanFamily,
) {
  if (plan.dedicated_ip.included > 0) {
    return t('labels.includedDedicatedIp', { count: plan.dedicated_ip.included });
  }

  return plan.dedicated_ip.eligible ? t('labels.dedicatedIpAddon') : false;
}

function formatInviteBundle(
  t: ReturnType<typeof useTranslations>,
  plan: PricingPlanFamily,
  selectedPeriod: number,
) {
  const activePeriod = getPlanPeriod(plan, selectedPeriod);

  if (activePeriod.invite_bundle.count <= 0) {
    return t('labels.inviteNone');
  }

  return t('labels.inviteBundle', {
    count: activePeriod.invite_bundle.count,
    days: activePeriod.invite_bundle.friend_days,
  });
}

export function FeatureMatrix({
  plans,
  addons,
  selectedPeriod,
}: {
  plans: PricingPlanFamily[];
  addons: PricingAddon[];
  selectedPeriod: number;
}) {
  const t = useTranslations('Pricing');
  const locale = useLocale();

  const rows = [
    {
      key: 'devices',
      name: t('matrix.rows.devices'),
      values: plans.map((plan) => t('labels.devices', { count: plan.devices_included })),
    },
    {
      key: 'traffic',
      name: t('matrix.rows.traffic'),
      values: plans.map((plan) => plan.traffic_policy.display_label),
    },
    {
      key: 'modes',
      name: t('matrix.rows.modes'),
      values: plans.map((plan) => formatModes(t, plan)),
    },
    {
      key: 'server-pool',
      name: t('matrix.rows.serverPool'),
      values: plans.map((plan) => formatServerPool(t, plan)),
    },
    {
      key: 'dedicated-ip',
      name: t('matrix.rows.dedicatedIp'),
      values: plans.map((plan) => formatDedicatedIp(t, plan)),
    },
    {
      key: 'support',
      name: t('matrix.rows.support'),
      values: plans.map((plan) => t(`supportNames.${plan.support_sla}`)),
    },
    {
      key: 'invites',
      name: t('matrix.rows.invites'),
      values: plans.map((plan) => formatInviteBundle(t, plan, selectedPeriod)),
    },
  ];

  const extraDeviceAddon = addons.find((addon) => addon.code === 'extra_device');
  const dedicatedIpAddon = addons.find((addon) => addon.code === 'dedicated_ip');
  const addonCards = [extraDeviceAddon, dedicatedIpAddon].filter(
    (addon): addon is PricingAddon => Boolean(addon),
  );

  return (
    <div className="w-full overflow-hidden rounded-[2rem] border border-white/10 bg-black/60 p-6 backdrop-blur-xl md:p-10">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h3 className="flex items-center gap-4 font-display text-2xl font-bold uppercase tracking-widest text-white">
            <span className="inline-block h-6 w-2 animate-pulse rounded-sm bg-neon-cyan" />
            {t('matrix.title')}
          </h3>
          <p className="mt-3 max-w-3xl text-sm font-mono leading-relaxed text-white/65">
            {t('matrix.subtitle')}
          </p>
        </div>
        <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-white/45">
          {t('summary.selectedTerm', { days: selectedPeriod })}
        </p>
      </div>

      <div className="md:hidden">
        <MobileDataList
          items={rows.map((row) => ({
            id: row.key,
            title: row.name,
            primaryFields: plans.map((plan, index) => ({
              label: plan.display_name,
              value: renderValue(
                row.values[index] ?? false,
                PLAN_TEXT_STYLES[plan.code],
              ),
            })),
          }))}
        />
      </div>

      <div className="hidden w-full overflow-x-auto pb-4 md:block">
        <table className="w-full min-w-[820px] border-collapse text-left">
          <thead>
            <tr className="border-b border-white/10 text-xs font-mono uppercase tracking-widest text-muted-foreground">
              <th className="w-[22%] px-4 py-4 font-normal">{t('matrix.rows.capability')}</th>
              {plans.map((plan) => (
                <th
                  key={plan.code}
                  className={`px-4 py-4 text-center font-normal ${PLAN_TEXT_STYLES[plan.code]}`}
                >
                  {plan.display_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-mono text-sm text-white/80">
            {rows.map((row, rowIndex) => (
              <motion.tr
                key={row.key}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: rowIndex * 0.05 }}
                className="group transition-colors hover:bg-white/[0.02]"
              >
                <td className="px-4 py-4 font-medium">{row.name}</td>
                {plans.map((plan, index) => (
                  <td
                    key={`${row.key}-${plan.code}`}
                    className="px-4 py-4 text-center align-top"
                  >
                    {renderValue(row.values[index] ?? false, PLAN_TEXT_STYLES[plan.code])}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-10 rounded-[1.75rem] border border-white/10 bg-white/[0.03] p-5 md:p-6">
        <div className="mb-5 flex items-center gap-3">
          <PlugZap className="h-5 w-5 text-neon-cyan" />
          <div>
            <h4 className="font-display text-xl font-bold uppercase tracking-[0.18em] text-white">
              {t('addons.title')}
            </h4>
            <p className="mt-1 text-sm font-mono text-white/62">
              {t('addons.subtitle')}
            </p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {addonCards.map((addon) => {
            const price = getPreferredCurrency(locale, {
              uuid: addon.uuid,
              name: addon.display_name,
              duration_days: selectedPeriod,
              price_usd: addon.price_usd,
              price_rub: addon.price_rub ?? null,
              invite_bundle: { count: 0, friend_days: 0, expiry_days: 0 },
              trial_eligible: false,
              sort_order: 0,
            });
            const availability = addon.code === 'extra_device'
              ? t('addons.extra_device.availability', {
                  limits: formatPlanLimitSummary(extraDeviceAddon, PLAN_ORDER),
                })
              : t('addons.dedicated_ip.availability');

            return (
              <div
                key={addon.code}
                className="rounded-[1.5rem] border border-white/10 bg-black/35 p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-display text-lg uppercase tracking-[0.14em] text-white">
                      {t(`addons.${addon.code}.title`)}
                    </p>
                    <p className="mt-3 text-sm font-mono leading-relaxed text-white/66">
                      {t(`addons.${addon.code}.description`)}
                    </p>
                  </div>
                  <div className="rounded-full border border-white/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/55">
                    {t('addons.priceLabel', {
                      price: formatMoney(locale, price.amount, price.currency),
                    })}
                  </div>
                </div>

                <div className="mt-4 flex items-start gap-2 text-sm font-mono text-white/75">
                  <Dot className="mt-0.5 h-4 w-4 shrink-0 text-neon-cyan" />
                  <span>{availability}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
