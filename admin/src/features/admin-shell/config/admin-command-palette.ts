import type { LucideIcon } from 'lucide-react';
import type { AdminRole } from '@/shared/lib/admin-rbac';
import type {
  AdminNavigationMessageKey,
  AdminNavGroupId,
  AdminNavHref,
  AdminNavItemRisk,
} from '@/features/admin-shell/config/admin-navigation';
import {
  resolveAdminNavigationGroups,
} from '@/features/admin-shell/config/admin-navigation';

export type AdminCommandPaletteProviderId = 'routes' | 'entities';
export type AdminCommandPaletteResultKind = 'route' | 'entity';

export interface AdminCommandPaletteResult {
  id: string;
  providerId: AdminCommandPaletteProviderId;
  kind: AdminCommandPaletteResultKind;
  href: AdminNavHref;
  icon: LucideIcon;
  label: string;
  description: string;
  groupId: AdminNavGroupId;
  groupLabel: string;
  risk: AdminNavItemRisk;
  searchText: string;
}

interface BuildAdminCommandPaletteResultsOptions {
  role: AdminRole | string | null | undefined;
  query: string;
  labelFor: (key: AdminNavigationMessageKey) => string;
  limit?: number;
}

const DEFAULT_RESULT_LIMIT = 10;

const SENSITIVE_RAW_QUERY_PATTERNS: readonly RegExp[] = [
  /\b(?:bearer|password|secret|token)\b/i,
  /\b(?:vmess|vless|trojan|ss):\/\//i,
  /https?:\/\/\S+/i,
  /[A-Za-z0-9_-]{36,}/,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
];

function normalizeSearchText(value: string): string {
  return value.trim().toLowerCase();
}

export function isSensitiveAdminCommandPaletteQuery(query: string): boolean {
  const trimmedQuery = query.trim();

  if (!trimmedQuery) {
    return false;
  }

  return SENSITIVE_RAW_QUERY_PATTERNS.some((pattern) =>
    pattern.test(trimmedQuery),
  );
}

function buildSearchText(parts: readonly string[]): string {
  return normalizeSearchText(parts.filter(Boolean).join(' '));
}

function scoreCommandPaletteResult(
  result: AdminCommandPaletteResult,
  normalizedQuery: string,
): number {
  if (!normalizedQuery) {
    return result.kind === 'entity' ? 90 : 80;
  }

  const normalizedLabel = normalizeSearchText(result.label);
  const normalizedGroupLabel = normalizeSearchText(result.groupLabel);

  if (normalizedLabel === normalizedQuery) {
    return 100;
  }

  if (normalizedLabel.startsWith(normalizedQuery)) {
    return 95;
  }

  if (normalizedGroupLabel.startsWith(normalizedQuery)) {
    return 85;
  }

  if (result.searchText.includes(normalizedQuery)) {
    return 70;
  }

  return 0;
}

function buildRouteProviderResults(
  role: AdminRole | string | null | undefined,
  labelFor: (key: AdminNavigationMessageKey) => string,
): AdminCommandPaletteResult[] {
  return resolveAdminNavigationGroups(role).flatMap((group) => {
    const groupLabel = labelFor(group.labelKey);

    return group.items
      .filter((item) => item.accessState === 'enabled')
      .map((item) => {
        const label = labelFor(item.labelKey);
        const description = labelFor(item.hintKey);

        return {
          id: `route:${item.id}`,
          providerId: 'routes',
          kind: 'route',
          href: item.href,
          icon: item.icon,
          label,
          description,
          groupId: group.id,
          groupLabel,
          risk: item.risk ?? 'read',
          searchText: buildSearchText([
            label,
            description,
            groupLabel,
            item.href,
            item.id,
          ]),
        };
      });
  });
}

function buildEntityProviderResults(
  role: AdminRole | string | null | undefined,
  labelFor: (key: AdminNavigationMessageKey) => string,
): AdminCommandPaletteResult[] {
  return resolveAdminNavigationGroups(role).flatMap((group) => {
    const enabledItems = group.items.filter(
      (item) => item.accessState === 'enabled',
    );

    if (enabledItems.length === 0) {
      return [];
    }

    const firstItem = enabledItems[0];
    const label = labelFor(group.labelKey);
    const description = labelFor(group.hintKey);
    const hasWriteRoute = enabledItems.some((item) => item.risk === 'write');
    const hasDangerRoute = enabledItems.some((item) => item.risk === 'danger');

    return [
      {
        id: `entity:${group.id}`,
        providerId: 'entities',
        kind: 'entity',
        href: firstItem.href,
        icon: firstItem.icon,
        label,
        description,
        groupId: group.id,
        groupLabel: label,
        risk: hasDangerRoute ? 'danger' : hasWriteRoute ? 'write' : 'read',
        searchText: buildSearchText([
          label,
          description,
          group.id,
          ...enabledItems.map((item) => labelFor(item.labelKey)),
        ]),
      },
    ];
  });
}

export function buildAdminCommandPaletteResults({
  role,
  query,
  labelFor,
  limit = DEFAULT_RESULT_LIMIT,
}: BuildAdminCommandPaletteResultsOptions): AdminCommandPaletteResult[] {
  const normalizedQuery = normalizeSearchText(query);

  if (isSensitiveAdminCommandPaletteQuery(query)) {
    return [];
  }

  return [
    ...buildEntityProviderResults(role, labelFor),
    ...buildRouteProviderResults(role, labelFor),
  ]
    .map((result) => ({
      result,
      score: scoreCommandPaletteResult(result, normalizedQuery),
    }))
    .filter(({ score }) => score > 0)
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }

      return left.result.label.localeCompare(right.result.label);
    })
    .slice(0, limit)
    .map(({ result }) => result);
}
