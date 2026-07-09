'use client';

import { Shield } from 'lucide-react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import {
  isAnyGrowthSurfaceEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';
import {
  getCabinetNavigationLabelFallback,
  getWebCabinetNavigationSections,
} from '@/widgets/dashboard-navigation';
import { NativeCabinetLink } from '@/widgets/native-cabinet-link';

export function CyberSidebar() {
  const pathname = usePathname();
  const t = useTranslations('Navigation');
  const { data: capabilities } = useClientCapabilities();
  const navSections = getWebCabinetNavigationSections({
    capabilities,
    growthVisible: isAnyGrowthSurfaceEnabled(capabilities),
  });
  const labelFor = (key: string) => {
    try {
      return t(key);
    } catch {
      return getCabinetNavigationLabelFallback(key);
    }
  };

  return (
    <aside
      aria-label={labelFor('sidebar')}
      className="fixed start-0 top-0 z-40 hidden h-dvh w-64 flex-col border-e border-grid-line/30 bg-terminal-surface/90 backdrop-blur-md md:flex"
    >
      <div className="flex h-16 items-center border-b border-grid-line/30 px-6">
        <div className="flex items-center gap-2 font-display text-xl tracking-wider text-neon-cyan drop-shadow-glow">
          <Shield className="h-6 w-6" />
          <span>NEXUS</span>
        </div>
      </div>

      <div className="custom-scrollbar flex-1 overflow-y-auto px-4 py-6 scrollbar-gutter-stable">
        <nav aria-label={labelFor('mainNavigation')} className="grid gap-5">
          {navSections.map((section) => (
            <div key={section.id}>
              <p className="px-3 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground/70">
                {labelFor(section.labelKey)}
              </p>
              <div className="mt-2 grid gap-1">
                {section.items.map((item) => {
                  const isActive = item.match(pathname);
                  const Icon = item.icon;
                  const label = labelFor(item.labelKey);

                  return (
                    <NativeCabinetLink
                      key={item.id}
                      href={item.href}
                      aria-label={label}
                      aria-current={isActive ? 'page' : undefined}
                      className="group relative block overflow-hidden rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                    >
                      {isActive && (
                        <motion.div
                          layoutId="sidebar-active"
                          className="absolute inset-0 border-s-2 border-neon-cyan bg-neon-cyan/10"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                        >
                          <div className="absolute inset-0 from-neon-cyan/20 to-transparent ltr:bg-gradient-to-r rtl:bg-gradient-to-l" />
                        </motion.div>
                      )}

                      <div
                        className={cn(
                          'relative flex items-center gap-3 px-4 py-3 text-sm font-mono transition-all duration-300',
                          isActive
                            ? 'text-neon-cyan ltr:translate-x-1 rtl:-translate-x-1'
                            : 'text-muted-foreground group-hover:text-foreground group-hover:ltr:translate-x-1 group-hover:rtl:-translate-x-1',
                        )}
                      >
                        <Icon
                          className={cn(
                            'h-4 w-4 transition-transform duration-300',
                            isActive
                              ? 'drop-shadow-[0_0_8px_cyan]'
                              : 'group-hover:scale-110 group-hover:drop-shadow-[0_0_5px_white]',
                          )}
                        />

                        <span className="relative tracking-wide">
                          <CypherText
                            text={label}
                            className="group-hover:text-neon-cyan transition-colors duration-300"
                            speed={30}
                          />
                          <span
                            aria-hidden="true"
                            className="absolute start-0 top-0 opacity-0 text-neon-pink mix-blend-screen ltr:-translate-x-[2px] rtl:translate-x-[2px] group-hover:opacity-100 group-hover:animate-pulse"
                          >
                            {label}
                          </span>
                          <span
                            aria-hidden="true"
                            className="animation-delay-75 absolute start-0 top-0 opacity-0 text-neon-cyan mix-blend-screen ltr:translate-x-[2px] rtl:-translate-x-[2px] group-hover:opacity-100 group-hover:animate-pulse"
                          >
                            {label}
                          </span>
                        </span>

                        {isActive && (
                          <motion.span
                            aria-hidden="true"
                            layoutId="active-dot"
                            className="absolute end-3 h-1.5 w-1.5 rounded-full bg-neon-cyan shadow-[0_0_8px_#00ffff]"
                          />
                        )}
                      </div>
                    </NativeCabinetLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      <div className="border-t border-grid-line/30 p-4">
        <div className="rounded-lg bg-sidebar-accent/50 p-3 border border-grid-line/20">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-neon-cyan/20 flex items-center justify-center text-neon-cyan border border-neon-cyan/50">
              CV
            </div>
            <div className="text-xs font-mono">
              <div className="text-foreground">USER NODE</div>
              <div className="text-muted-foreground">PRIVATE ACCESS</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
