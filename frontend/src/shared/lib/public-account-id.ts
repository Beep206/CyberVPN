const PUBLIC_UID_MIN = 10_000_000;
const PUBLIC_UID_MAX = 99_999_999;

export function formatCustomerPublicUid(value: number | string | null | undefined): string | null {
  if (typeof value === 'number') {
    return Number.isInteger(value) && value >= PUBLIC_UID_MIN && value <= PUBLIC_UID_MAX
      ? String(value)
      : null;
  }

  const normalized = value?.trim();
  if (!normalized || !/^\d+$/.test(normalized)) {
    return null;
  }

  const numericValue = Number(normalized);
  return numericValue >= PUBLIC_UID_MIN && numericValue <= PUBLIC_UID_MAX ? normalized : null;
}
