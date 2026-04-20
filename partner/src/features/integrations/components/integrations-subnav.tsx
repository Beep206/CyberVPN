'use client';

import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { INTEGRATIONS_NAV_ITEMS } from '@/features/integrations/config/navigation';

export function IntegrationsSubnav() {
  const pathname = usePathname();
  const t = useTranslations('Integrations');

  return (
    <nav
      aria-label={t('layout.subnavLabel')}
      className="overflow-x-auto rounded-2xl border border-grid-line/20 bg-terminal-surface/40 p-2 backdrop-blur"
    >
      <div className="flex min-w-max gap-2">
        {INTEGRATIONS_NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.href
            || (item.href !== '/integrations'
              && pathname?.startsWith(`${item.href}/`));

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'rounded-xl border px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] transition-colors',
                isActive
                  ? 'border-neon-cyan/35 bg-neon-cyan/10 text-neon-cyan'
                  : 'border-grid-line/20 bg-terminal-bg/50 text-muted-foreground hover:border-grid-line/40 hover:text-white',
              )}
            >
              {t(item.labelKey)}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
