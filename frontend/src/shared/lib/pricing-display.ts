export const S1_BILLING_CURRENCY = 'USD';
export const S1_LOCAL_DISPLAY_RATE_VERSION = 'stage1-static-display-rates-v1';

type LocalDisplayRule = {
  currency: 'RUB';
  localePrefixes: readonly string[];
  usdRate: number;
  roundIncrement: number;
};

export type MoneyAmount = {
  amount: number;
  currency: string;
};

export type LocalDisplayEstimate = MoneyAmount & {
  source: 'catalog' | 'stage1_static_rate';
  rateVersion: string;
};

export type PricePresentation = {
  billing: MoneyAmount;
  localEstimate: LocalDisplayEstimate | null;
};

const LOCAL_DISPLAY_RULES: readonly LocalDisplayRule[] = [
  {
    currency: 'RUB',
    localePrefixes: ['ru'],
    usdRate: 100,
    roundIncrement: 10,
  },
];

function normalizeLocale(locale: string): string {
  return locale.trim().toLowerCase();
}

function getLocalDisplayRule(locale: string): LocalDisplayRule | null {
  const normalizedLocale = normalizeLocale(locale);

  return (
    LOCAL_DISPLAY_RULES.find((rule) =>
      rule.localePrefixes.some((prefix) => normalizedLocale.startsWith(prefix)),
    ) ?? null
  );
}

function isPositiveFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

function roundUpToIncrement(amount: number, increment: number): number {
  if (increment <= 0) {
    return Math.ceil(amount);
  }

  return Math.ceil(amount / increment) * increment;
}

export function formatMoney(locale: string, amount: number, currency: string) {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
  }).format(amount);
}

export function getLocalDisplayEstimate(
  locale: string,
  priceUsd: number,
  localAmount?: number | null,
): LocalDisplayEstimate | null {
  const rule = getLocalDisplayRule(locale);
  if (!rule || !isPositiveFiniteNumber(priceUsd)) {
    return null;
  }

  const sourceAmount = isPositiveFiniteNumber(localAmount)
    ? localAmount
    : priceUsd * rule.usdRate;

  return {
    amount: roundUpToIncrement(sourceAmount, rule.roundIncrement),
    currency: rule.currency,
    source: isPositiveFiniteNumber(localAmount) ? 'catalog' : 'stage1_static_rate',
    rateVersion: S1_LOCAL_DISPLAY_RATE_VERSION,
  };
}

export function getPricePresentation(
  locale: string,
  price: { price_usd: number; price_rub?: number | null },
): PricePresentation {
  return {
    billing: {
      amount: price.price_usd,
      currency: S1_BILLING_CURRENCY,
    },
    localEstimate: getLocalDisplayEstimate(locale, price.price_usd, price.price_rub),
  };
}
