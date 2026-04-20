export function formatCurrencyAmount(amount: number | undefined, currency = 'USD') {
  if (typeof amount !== 'number' || Number.isNaN(amount)) {
    return '--';
  }

  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatCompactNumber(value: number | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--';
  }

  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: value >= 1000 ? 1 : 0,
  }).format(value);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return 'Unknown';
  }

  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function shortId(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value.slice(0, 8);
}

export function parseFeatureLines(rawValue: string) {
  return rawValue
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}
