import {
  getDefaultCurrencyForLocale,
  isSupportedCurrency,
  type SupportedCurrency,
} from '@/features/currency-selector/currency-config';

export const S1_BILLING_CURRENCY = 'USD';
export const S2_DISPLAY_RATE_VERSION = 's2-static-display-rates-2026-05-25';

type DisplayCurrencyRule = {
  usdRate: number;
  roundIncrement: number;
};

export type MoneyAmount = {
  amount: number;
  currency: string;
};

export type LocalDisplayEstimate = MoneyAmount & {
  source: 'catalog' | 's2_static_rate';
  rateVersion: string;
};

export type PricePresentation = {
  billing: MoneyAmount;
  localEstimate: LocalDisplayEstimate | null;
};

const DISPLAY_CURRENCY_RULES: Record<SupportedCurrency, DisplayCurrencyRule> = {
  USD: { usdRate: 1, roundIncrement: 0.01 },
  RUB: { usdRate: 100, roundIncrement: 10 },
  EUR: { usdRate: 0.92, roundIncrement: 0.01 },
  CNY: { usdRate: 7.2, roundIncrement: 1 },
  INR: { usdRate: 83, roundIncrement: 1 },
  IDR: { usdRate: 16000, roundIncrement: 1000 },
  VND: { usdRate: 25000, roundIncrement: 1000 },
  THB: { usdRate: 36, roundIncrement: 1 },
  JPY: { usdRate: 155, roundIncrement: 100 },
  KRW: { usdRate: 1370, roundIncrement: 100 },
  SAR: { usdRate: 3.75, roundIncrement: 1 },
  IRR: { usdRate: 42000, roundIncrement: 1000 },
  TRY: { usdRate: 32, roundIncrement: 1 },
  PKR: { usdRate: 278, roundIncrement: 10 },
  BDT: { usdRate: 117, roundIncrement: 10 },
  MYR: { usdRate: 4.7, roundIncrement: 1 },
  KZT: { usdRate: 450, roundIncrement: 10 },
  BYN: { usdRate: 3.25, roundIncrement: 1 },
  MMK: { usdRate: 2100, roundIncrement: 100 },
  UZS: { usdRate: 12600, roundIncrement: 1000 },
  NGN: { usdRate: 1500, roundIncrement: 100 },
  IQD: { usdRate: 1310, roundIncrement: 100 },
  ETB: { usdRate: 57, roundIncrement: 5 },
  TMT: { usdRate: 3.5, roundIncrement: 1 },
  TWD: { usdRate: 32, roundIncrement: 1 },
  ILS: { usdRate: 3.7, roundIncrement: 1 },
  PLN: { usdRate: 4, roundIncrement: 1 },
  PHP: { usdRate: 58, roundIncrement: 5 },
  UAH: { usdRate: 40, roundIncrement: 1 },
  CZK: { usdRate: 23, roundIncrement: 1 },
  RON: { usdRate: 4.6, roundIncrement: 1 },
  HUF: { usdRate: 360, roundIncrement: 10 },
  SEK: { usdRate: 10.5, roundIncrement: 1 },
};

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
  currencyOverride?: string | null,
): LocalDisplayEstimate | null {
  const currency = isSupportedCurrency(currencyOverride)
    ? currencyOverride
    : getDefaultCurrencyForLocale(locale);
  const rule = DISPLAY_CURRENCY_RULES[currency];
  if (!rule || !isPositiveFiniteNumber(priceUsd)) {
    return null;
  }

  const sourceAmount = currency === 'RUB' && isPositiveFiniteNumber(localAmount)
    ? localAmount
    : priceUsd * rule.usdRate;

  return {
    amount: roundUpToIncrement(sourceAmount, rule.roundIncrement),
    currency,
    source: currency === 'RUB' && isPositiveFiniteNumber(localAmount) ? 'catalog' : 's2_static_rate',
    rateVersion: S2_DISPLAY_RATE_VERSION,
  };
}

export function getPricePresentation(
  locale: string,
  price: { price_usd: number; price_rub?: number | null },
  currencyOverride?: string | null,
): PricePresentation {
  const display = getLocalDisplayEstimate(locale, price.price_usd, price.price_rub, currencyOverride);

  return {
    billing: {
      amount: display?.amount ?? price.price_usd,
      currency: display?.currency ?? S1_BILLING_CURRENCY,
    },
    localEstimate: display,
  };
}
