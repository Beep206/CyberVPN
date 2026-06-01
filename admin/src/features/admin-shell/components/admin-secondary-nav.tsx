'use client';

import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';
import {
  ADMIN_NAV_LABEL_FALLBACKS,
  getAdminActiveNavItem,
  resolveAdminNavigationGroups,
} from '@/features/admin-shell/config/admin-navigation';
import type {
  AdminNavigationMessageKey,
  AdminNavGroupId,
  ResolvedAdminNavItem,
} from '@/features/admin-shell/config/admin-navigation';

interface AdminSecondaryNavProps {
  groupId: AdminNavGroupId;
  className?: string;
}

export function AdminSecondaryNav({
  groupId,
  className,
}: AdminSecondaryNavProps) {
  const pathname = usePathname();
  const t = useTranslations('Navigation');
  const user = useAuthStore((state) => state.user);
  const groups = resolveAdminNavigationGroups(user?.role);
  const group = groups.find((candidate) => candidate.id === groupId);

  const labelFor = (key: AdminNavigationMessageKey) => {
    try {
      return t(key);
    } catch {
      return ADMIN_NAV_LABEL_FALLBACKS[key];
    }
  };

  if (!group) {
    return null;
  }

  const activeItem = getAdminActiveNavItem(pathname, [group]);
  const activeItemId = activeItem?.id ?? null;
  const groupLabel = labelFor(group.labelKey);
  const groupHint = labelFor(group.hintKey);

  const renderItem = (item: ResolvedAdminNavItem) => {
    const label = labelFor(item.labelKey);
    const hint = labelFor(item.hintKey);
    const isActive = item.id === activeItemId;
    const isDisabled = item.accessState === 'disabled';
    const Icon = item.icon;
    const content = (
      <>
        <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
        <span className="min-w-0">
          <span className="block truncate">{label}</span>
          <span
            aria-hidden="true"
            className={cn(
              'mt-0.5 hidden truncate text-[10px] normal-case tracking-[0.08em] md:block',
              isActive ? 'text-neon-cyan/75' : 'text-muted-foreground/75',
            )}
          >
            {hint}
          </span>
        </span>
      </>
    );
    const itemClassName = cn(
      'group inline-grid min-h-11 min-w-[9.5rem] max-w-[16rem] grid-cols-[auto_minmax(0,1fr)] items-center gap-2 rounded-lg border px-3 py-2 text-left font-mono text-[11px] uppercase tracking-[0.14em] transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg sm:min-w-[10.5rem]',
      isActive
        ? 'border-neon-cyan/45 bg-neon-cyan/10 text-neon-cyan shadow-[0_0_18px_rgba(0,255,255,0.10)]'
        : 'border-grid-line/20 bg-terminal-bg/55 text-muted-foreground hover:border-grid-line/50 hover:bg-terminal-bg/75 hover:text-foreground',
      isDisabled
        ? 'cursor-not-allowed opacity-55 hover:border-grid-line/20 hover:bg-terminal-bg/55 hover:text-muted-foreground'
        : '',
    );

    if (isDisabled) {
      return (
        <span
          key={item.id}
          role="link"
          aria-label={label}
          aria-current={isActive ? 'page' : undefined}
          aria-disabled="true"
          title={hint}
          className={itemClassName}
        >
          {content}
        </span>
      );
    }

    return (
      <Link
        key={item.id}
        href={item.href}
        aria-label={label}
        aria-current={isActive ? 'page' : undefined}
        title={hint}
        className={itemClassName}
      >
        {content}
      </Link>
    );
  };

  return (
    <nav
      aria-label={labelFor('secondaryNavigation')}
      className={cn(
        'rounded-lg border border-grid-line/20 bg-terminal-surface/45 px-3 py-3 backdrop-blur',
        className,
      )}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="min-w-0 lg:w-56 lg:shrink-0">
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-neon-cyan">
            {groupLabel}
          </div>
          <div className="mt-1 truncate text-xs text-muted-foreground">
            {groupHint}
          </div>
        </div>

        <div className="-mx-1 overflow-x-auto pb-1">
          <div className="flex min-w-max gap-2 px-1">
            {group.items.map((item) => renderItem(item))}
          </div>
        </div>
      </div>
    </nav>
  );
}
