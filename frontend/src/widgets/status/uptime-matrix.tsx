'use client';

import { useLocale, useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Database } from 'lucide-react';
import type {
  PublicNetworkUptimeHistoryDay,
  PublicNetworkUptimeResponse,
} from '@/lib/api/public-network';
import { formatAvailability, formatCount } from '@/features/network-intelligence/lib/public-network';

interface UptimeMatrixProps {
  history: PublicNetworkUptimeHistoryDay[];
  uptime?: PublicNetworkUptimeResponse;
}

export function UptimeMatrix({ history, uptime }: UptimeMatrixProps) {
  const locale = useLocale();
  const t = useTranslations('Status');

  const getColorClass = (status: PublicNetworkUptimeHistoryDay['status']) => {
    switch (status) {
      case 'nominal':
        return 'bg-matrix-green hover:shadow-[0_0_10px_#00ff88]';
      case 'warning':
        return 'bg-warning hover:shadow-[0_0_10px_#ffb800]';
      case 'outage':
        return 'bg-destructive animate-pulse hover:shadow-[0_0_15px_#ff0055]';
      case 'maintenance':
        return 'bg-neon-cyan hover:shadow-[0_0_10px_#00ffff]';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.2 }}
      className="w-full border border-white/10 bg-black/60 backdrop-blur-xl rounded-xl p-4 md:p-6"
    >
      <div className="flex justify-between items-end mb-6 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-5 h-5 text-neon-cyan" />
            <h2 className="text-xl font-display font-bold text-white uppercase tracking-wider">
              {t('history.title')}
            </h2>
          </div>
          <p className="font-mono text-xs text-matrix-green uppercase tracking-widest">
            {t('metrics.uptime')}
          </p>
        </div>

        <div className="text-right">
          <p className="font-display text-2xl font-black text-white">
            {formatAvailability(uptime?.summary.currentAvailabilityPct, locale)}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-white/35">
            {formatCount(uptime?.summary.coverageDays, locale)} / {formatCount(uptime?.summary.windowDays, locale)}
          </p>
        </div>
      </div>

      {history.length > 0 ? (
        <>
          <div className="w-full overflow-x-auto custom-scrollbar pb-2">
            <div className="flex gap-1 min-w-max">
              {history.map((day) => (
                <div
                  key={day.date}
                  className={`w-3 h-10 rounded-sm transition-all duration-300 cursor-crosshair group relative ${getColorClass(day.status)}`}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max px-2 py-1 bg-black border border-white/20 rounded-md opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none">
                    <p className="font-mono text-[10px] text-white">
                      {day.date}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 flex justify-between font-mono text-[10px] text-white/30 uppercase">
            <span>-90 {t('history.tooltip_date')}</span>
            <span>Today</span>
          </div>
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] min-h-[220px] flex items-center justify-center">
          <div className="text-center px-6">
            <p className="font-display text-4xl font-black text-white">
              {formatAvailability(uptime?.summary.currentAvailabilityPct, locale)}
            </p>
            <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.3em] text-white/35">
              {formatCount(uptime?.summary.coverageDays, locale)} / {formatCount(uptime?.summary.windowDays, locale)}
            </p>
          </div>
        </div>
      )}
    </motion.div>
  );
}
