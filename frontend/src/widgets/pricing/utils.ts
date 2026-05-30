import type {
  PricingAddon,
  PricingCatalogMoney,
  PricingCatalogData,
  PricingPlanFamily,
  PricingPlanPeriod,
  PricingTierCode,
} from '@/widgets/pricing/types';
import {
  formatMoney,
  getPricePresentation,
} from '@/shared/lib/pricing-display';

export { formatMoney, getPricePresentation };

export function getCatalogMoneyAmount(money: PricingCatalogMoney): number {
  const amount = Number(money.amount);
  return Number.isFinite(amount) ? amount : 0;
}

export function formatCatalogMoney(locale: string, money: PricingCatalogMoney) {
  return formatMoney(locale, getCatalogMoneyAmount(money), money.currency);
}

export function getBillingPrice(_locale: string, period: PricingPlanPeriod) {
  return {
    amount: getCatalogMoneyAmount(period.display_price),
    currency: period.display_price.currency,
  };
}

export function getLocalPriceEstimate(_locale: string, period: PricingPlanPeriod) {
  return {
    amount: getCatalogMoneyAmount(period.display_price),
    currency: period.display_price.currency,
    source: 'catalog' as const,
    rateVersion: period.version,
  };
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
