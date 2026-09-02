'use client';

import Link from 'next/link';
import { ArrowUpRight, CircleOff, LockKeyhole, Waypoints } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { AdminRemnawaveCapabilitiesAndStreams } from '@/lib/api/remnawave-status';
import { useAuthStore } from '@/stores/auth-store';
import {
  hasAdminPermission,
  type AdminPermission,
} from '@/shared/lib/admin-rbac';

type CapabilityKey = keyof AdminRemnawaveCapabilitiesAndStreams['capabilities'];
type OperatorSurfaceKey =
  | 'users'
  | 'stats'
  | 'nodes'
  | 'hosts'
  | 'profiles'
  | 'squads'
  | 'snippets'
  | 'plugins'
  | 'integrations'
  | 'systemConfig'
  | 'connections'
  | 'tags'
  | 'sharedLists'
  | 'geoCheck'
  | 'responseRules';

interface OperatorSurface {
  key: OperatorSurfaceKey;
  href?: string;
  capability?: CapabilityKey;
  requiredPermissions: readonly AdminPermission[];
  permissionMode?: 'all' | 'any';
}

const OPERATOR_SURFACES: readonly OperatorSurface[] = [
  { key: 'users', href: '/customers', requiredPermissions: ['user_read'] },
  {
    key: 'stats',
    href: '/dashboard',
    requiredPermissions: ['monitoring_read', 'view_analytics'],
    permissionMode: 'any',
  },
  { key: 'nodes', href: '/infrastructure/servers', requiredPermissions: ['server_read'] },
  {
    key: 'hosts',
    href: '/infrastructure/hosts',
    capability: 'host_mapper',
    requiredPermissions: ['server_read'],
  },
  {
    key: 'profiles',
    href: '/infrastructure/config-profiles',
    requiredPermissions: ['server_read'],
  },
  { key: 'squads', href: '/infrastructure/squads', requiredPermissions: ['server_read'] },
  {
    key: 'snippets',
    href: '/infrastructure/remnawave/operator',
    capability: 'root_snippets',
    requiredPermissions: ['server_read', 'user_delete'],
  },
  {
    key: 'plugins',
    href: '/infrastructure/node-plugins',
    requiredPermissions: ['server_read'],
  },
  {
    key: 'integrations',
    href: '/infrastructure/remnawave/operator',
    capability: 'node_integrations',
    requiredPermissions: ['server_read', 'user_delete'],
  },
  {
    key: 'systemConfig',
    href: '/governance/policy',
    requiredPermissions: ['audit_read', 'manage_admins'],
    permissionMode: 'any',
  },
  {
    key: 'connections',
    href: '/infrastructure/remnawave/connections',
    capability: 'connections',
    requiredPermissions: ['monitoring_read'],
  },
  { key: 'tags', href: '/infrastructure/remnawave/operator', capability: 'tags', requiredPermissions: ['server_read', 'user_delete'] },
  { key: 'sharedLists', href: '/infrastructure/remnawave/operator', capability: 'shared_lists', requiredPermissions: ['server_read', 'user_delete'] },
  { key: 'geoCheck', href: '/infrastructure/remnawave/operator', capability: 'geo_check', requiredPermissions: ['server_read', 'user_delete'] },
  { key: 'responseRules', requiredPermissions: ['server_read'] },
] as const;

function hasRequiredPermissions(
  role: string | null | undefined,
  surface: OperatorSurface,
): boolean {
  if (surface.permissionMode === 'any') {
    return surface.requiredPermissions.some((permission) =>
      hasAdminPermission(role, permission),
    );
  }
  return surface.requiredPermissions.every((permission) =>
    hasAdminPermission(role, permission),
  );
}

export function RemnawaveOperatorDirectory({
  capabilities,
}: {
  capabilities: AdminRemnawaveCapabilitiesAndStreams['capabilities'];
}) {
  const t = useTranslations('Infrastructure.remnawave.operatorHub');
  const role = useAuthStore((state) => state.user?.role);

  return (
    <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6">
      <div className="flex items-start gap-3">
        <Waypoints className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
            {t('eyebrow')}
          </p>
          <h2 className="mt-2 font-display text-xl text-white">{t('title')}</h2>
          <p className="mt-2 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
            {t('description')}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {OPERATOR_SURFACES.map((surface) => {
          const permitted = hasRequiredPermissions(role, surface);
          const deployed = surface.capability ? capabilities[surface.capability] : true;
          const actionable = Boolean(surface.href) && permitted && deployed;
          const state = !permitted ? 'locked' : !surface.href ? 'notExposed' : !deployed ? 'disabled' : 'open';

          return (
            <article
              key={surface.key}
              className="flex min-h-40 flex-col rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-base text-white">
                    {t(`items.${surface.key}.title`)}
                  </h3>
                  <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
                    {t(`items.${surface.key}.description`)}
                  </p>
                </div>
                {state === 'locked' ? (
                  <LockKeyhole className="h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
                ) : state === 'notExposed' || state === 'disabled' ? (
                  <CircleOff className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                ) : null}
              </div>

              <div className="mt-auto pt-4">
                {actionable && surface.href ? (
                  <Link
                    href={surface.href}
                    className="inline-flex min-h-11 items-center rounded-lg border border-neon-cyan/35 px-3 py-2 font-mono text-xs uppercase tracking-[0.12em] text-neon-cyan transition-colors hover:border-neon-cyan focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan"
                  >
                    {t('open')}
                    <ArrowUpRight className="ml-2 h-4 w-4" aria-hidden="true" />
                  </Link>
                ) : (
                  <p className="font-mono text-xs text-amber-200" role="status">
                    {t(`states.${state}`)}
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
