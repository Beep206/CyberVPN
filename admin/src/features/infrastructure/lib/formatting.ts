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

export function formatBytes(value: number | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--';
  }

  if (value === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const power = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1,
  );
  const scaled = value / 1024 ** power;

  return `${scaled.toFixed(scaled >= 100 || power === 0 ? 0 : 1)} ${units[power]}`;
}

export function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return 'Unknown';
  }

  return value
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function shortId(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value.slice(0, 8);
}

export function parseLineList(rawValue: string) {
  return rawValue
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function parseCsvList(rawValue: string) {
  return rawValue
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function stringifyJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

export function parseJsonObject(rawValue: string) {
  if (!rawValue.trim()) {
    return {};
  }

  const parsed = JSON.parse(rawValue) as unknown;

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('Expected a JSON object');
  }

  return parsed as Record<string, unknown>;
}
