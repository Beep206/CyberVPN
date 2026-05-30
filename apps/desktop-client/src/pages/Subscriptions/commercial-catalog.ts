import type { PublicCommercialCatalogResponse } from "../../shared/api/ipc";

export interface DesktopCommercialCatalogOption {
  id: string;
  planCode: string;
  displayName: string;
  durationDays: number;
  amount: number;
  currency: string;
  devicesIncluded: number;
  trafficLimitBytes: number | null;
  quoteCatalogItemKey: string;
  quoteContextCacheKey: string;
}

const PLAN_ORDER = ["basic", "plus", "pro", "max"];

function getPlanOrder(planCode: string): number {
  const index = PLAN_ORDER.indexOf(planCode);
  return index === -1 ? Number.MAX_SAFE_INTEGER : index;
}

export function flattenCommercialCatalogPlans(
  catalog: PublicCommercialCatalogResponse,
): DesktopCommercialCatalogOption[] {
  return catalog.plans
    .flatMap((plan) =>
      plan.billingPeriods.map((period) => ({
        id: period.quote.planId || period.planId,
        planCode: plan.planCode,
        displayName: plan.displayName,
        durationDays: period.durationDays,
        amount: Number(period.displayPrice.amount),
        currency: period.displayPrice.currency,
        devicesIncluded: plan.devicesIncluded,
        trafficLimitBytes: plan.trafficLimitBytes,
        quoteCatalogItemKey: period.quote.catalogItemKey,
        quoteContextCacheKey: period.quote.contextCacheKey,
      })),
    )
    .filter((option) => Number.isFinite(option.amount))
    .sort((left, right) => {
      const planOrder =
        getPlanOrder(left.planCode) - getPlanOrder(right.planCode);
      if (planOrder !== 0) return planOrder;
      return left.durationDays - right.durationDays;
    });
}

export function formatCatalogPrice(
  amount: number,
  currency: string,
  locale?: string,
): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`;
  }
}
