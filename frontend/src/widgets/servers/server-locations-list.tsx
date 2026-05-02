'use client';

import { motion } from 'motion/react';
import { useLocale } from 'next-intl';
import { Globe2, Server, Users } from 'lucide-react';
import type { PublicNetworkRegion } from '@/lib/api/public-network';
import { cn } from '@/lib/utils';
import {
  formatCount,
  formatTraffic,
  resolveCountryLabel,
} from '@/features/network-intelligence/lib/public-network';

interface ServerLocationsListProps {
  activeNodeId: string | null;
  regions: PublicNetworkRegion[];
  setActiveNodeId: (id: string | null) => void;
}

export function ServerLocationsList({
  activeNodeId,
  regions,
  setActiveNodeId,
}: ServerLocationsListProps) {
  const locale = useLocale();

  if (!regions.length) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={index}
            className="h-[74px] rounded-lg border border-grid-line/20 bg-terminal-bg/60 backdrop-blur-md"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-2">
      {regions.map((region, index) => {
        const isActive = activeNodeId === region.id;
        const regionLabel = resolveCountryLabel(region.countryCode, locale);
        const onlineServersLabel = `${formatCount(region.onlineServers, locale)} / ${formatCount(region.totalServers, locale)}`;

        return (
          <motion.button
            key={region.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: index * 0.04 }}
            onMouseEnter={() => setActiveNodeId(region.id)}
            onFocus={() => setActiveNodeId(region.id)}
            className={cn(
              'relative w-full text-left p-4 rounded-lg border transition-all duration-300 group overflow-hidden',
              isActive
                ? 'bg-neon-cyan/10 border-neon-cyan shadow-[0_0_20px_rgba(0,255,255,0.1)]'
                : 'bg-terminal-bg/80 backdrop-blur-md border-grid-line/30 hover:border-neon-cyan/50 hover:bg-terminal-bg',
            )}
          >
            <div
              className={cn(
                'absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full transition-transform duration-700',
                isActive ? 'animate-scan' : 'group-hover:translate-x-[200%]',
              )}
            />

            <div className="relative z-10 flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full transition-all duration-300',
                      region.status === 'online'
                        ? 'bg-matrix-green shadow-[0_0_8px_rgba(0,255,136,0.8)]'
                        : region.status === 'degraded'
                          ? 'bg-warning shadow-[0_0_8px_rgba(255,184,0,0.65)]'
                          : 'bg-destructive shadow-[0_0_8px_rgba(255,0,85,0.65)]',
                    )}
                  />
                  <span
                    className={cn(
                      'font-mono text-sm transition-colors duration-300 truncate',
                      isActive ? 'text-white font-bold' : 'text-muted-foreground group-hover:text-white',
                    )}
                  >
                    {regionLabel}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-[11px] text-white/55">
                  <span className="inline-flex items-center gap-1.5">
                    <Server className="h-3 w-3 text-matrix-green/70" />
                    {onlineServersLabel}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="h-3 w-3 text-neon-cyan/70" />
                    {formatCount(region.activeUsers, locale)}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Globe2 className="h-3 w-3 text-neon-pink/70" />
                    {formatTraffic(region.totalTrafficBytes, locale)}
                  </span>
                </div>
              </div>

              <span
                className={cn(
                  'font-mono text-[10px] uppercase tracking-[0.24em]',
                  region.status === 'online'
                    ? 'text-matrix-green/70'
                    : region.status === 'degraded'
                      ? 'text-warning/80'
                      : 'text-destructive/80',
                )}
              >
                {region.countryCode}
              </span>
            </div>

            {isActive ? (
              <motion.div
                layoutId="activeRegionGlow"
                className="absolute inset-0 rounded-lg border border-neon-cyan pointer-events-none"
                initial={false}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            ) : null}
          </motion.button>
        );
      })}
    </div>
  );
}
