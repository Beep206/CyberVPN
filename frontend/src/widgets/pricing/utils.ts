import type {
  PricingAddon,
  PricingCatalogData,
  PricingPlanFamily,
  PricingPlanPeriod,
  PricingTierCode,
} from '@/widgets/pricing/types';

export function getPreferredCurrency(locale: string, period: PricingPlanPeriod) {
  if (locale.startsWith('ru') && typeof period.price_rub === 'number' && period.price_rub > 0) {
    return { amount: period.price_rub, currency: 'RUB' };
  }

  return { amount: period.price_usd, currency: 'USD' };
}

export function formatMoney(locale: string, amount: number, currency: string) {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

export function getPlanPeriod(
  plan: PricingPlanFamily,
  selectedPeriod: number,
): PricingPlanPeriod {
  return (
    plan.periods.find((period) => period.duration_days === selectedPeriod)
    ?? plan.periods[plan.periods.length - 1]
  );
}

export function getCatalogDefaultPeriod(catalog: PricingCatalogData) {
  return catalog.periods.includes(365)
    ? 365
    : catalog.periods[catalog.periods.length - 1] ?? 30;
}

export function getAddonByCode(catalog: PricingCatalogData, code: string) {
  return catalog.addons.find((addon) => addon.code === code);
}

export function formatPlanLimitSummary(
  addon: PricingAddon | undefined,
  order: readonly PricingTierCode[],
) {
  if (!addon) {
    return '';
  }

  return order
    .map((planCode) => {
      const limit = addon.max_quantity_by_plan[planCode];
      return typeof limit === 'number' ? `${planCode} +${limit}` : null;
    })
    .filter(Boolean)
    .join(' · ');
}
