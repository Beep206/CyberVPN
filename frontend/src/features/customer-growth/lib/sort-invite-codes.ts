export type InviteCodeSortItem = {
  id?: string | null;
  status?: string | null;
  is_used?: boolean | null;
  is_redeemable?: boolean | null;
  status_sort_order?: number | null;
  created_at?: string | null;
  expires_at?: string | null;
  used_at?: string | null;
  revoked_at?: string | null;
  blocked_at?: string | null;
  updated_at?: string | null;
};

type SortOptions = {
  now?: number;
};

const ACTIVE_STATUSES = new Set(['active', 'issued', 'redeemable']);
const USED_STATUSES = new Set(['redeemed', 'used', 'exhausted']);
const EXPIRED_STATUSES = new Set(['expired']);
const REVOKED_STATUSES = new Set(['revoked', 'blocked']);

const SORT_ORDER = {
  active: 0,
  used: 2,
  expired: 3,
  revoked: 4,
  unknown: 5,
} as const;

function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }

  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function normalizeStatus(value: string | null | undefined): string {
  return value?.trim().toLowerCase().replaceAll('-', '_') ?? '';
}

function fallbackStatusSortOrder(item: InviteCodeSortItem, now: number): number {
  const status = normalizeStatus(item.status);

  if (REVOKED_STATUSES.has(status)) {
    return SORT_ORDER.revoked;
  }

  if (USED_STATUSES.has(status) || item.is_used === true) {
    return SORT_ORDER.used;
  }

  if (EXPIRED_STATUSES.has(status)) {
    return SORT_ORDER.expired;
  }

  const expiresAt = parseTimestamp(item.expires_at);
  if (expiresAt !== null && expiresAt <= now) {
    return SORT_ORDER.expired;
  }

  if (
    item.is_redeemable === true ||
    ACTIVE_STATUSES.has(status) ||
    !status
  ) {
    return SORT_ORDER.active;
  }

  return SORT_ORDER.unknown;
}

function statusSortOrder(item: InviteCodeSortItem, now: number): number {
  return typeof item.status_sort_order === 'number' && Number.isFinite(item.status_sort_order)
    ? item.status_sort_order
    : fallbackStatusSortOrder(item, now);
}

function primaryTimestamp(item: InviteCodeSortItem, order: number): number {
  if (order === SORT_ORDER.active || order === 1) {
    return parseTimestamp(item.expires_at) ?? Number.POSITIVE_INFINITY;
  }

  if (order === SORT_ORDER.used || item.status_sort_order === SORT_ORDER.used) {
    return -(parseTimestamp(item.used_at) ?? Number.NEGATIVE_INFINITY);
  }

  if (
    order === SORT_ORDER.expired ||
    order === SORT_ORDER.revoked ||
    item.status_sort_order === SORT_ORDER.expired ||
    item.status_sort_order === SORT_ORDER.revoked
  ) {
    return -(
      parseTimestamp(item.revoked_at) ??
      parseTimestamp(item.blocked_at) ??
      parseTimestamp(item.updated_at) ??
      parseTimestamp(item.expires_at) ??
      Number.NEGATIVE_INFINITY
    );
  }

  return Number.POSITIVE_INFINITY;
}

function createdAtFallback(item: InviteCodeSortItem): number {
  return -(parseTimestamp(item.created_at) ?? Number.NEGATIVE_INFINITY);
}

export function sortInviteCodes<T extends InviteCodeSortItem>(
  items: readonly T[],
  options: SortOptions = {},
): T[] {
  const now = options.now ?? Date.now();

  return items
    .map((item, index) => ({ item, index }))
    .sort((left, right) => {
      const leftOrder = statusSortOrder(left.item, now);
      const rightOrder = statusSortOrder(right.item, now);
      if (leftOrder !== rightOrder) {
        return leftOrder - rightOrder;
      }

      const leftTimestamp = primaryTimestamp(left.item, leftOrder);
      const rightTimestamp = primaryTimestamp(right.item, rightOrder);
      if (leftTimestamp !== rightTimestamp) {
        return leftTimestamp - rightTimestamp;
      }

      const leftCreatedAt = createdAtFallback(left.item);
      const rightCreatedAt = createdAtFallback(right.item);
      if (leftCreatedAt !== rightCreatedAt) {
        return leftCreatedAt - rightCreatedAt;
      }

      const leftId = left.item.id ?? '';
      const rightId = right.item.id ?? '';
      if (leftId !== rightId) {
        return leftId.localeCompare(rightId);
      }

      return left.index - right.index;
    })
    .map(({ item }) => item);
}
