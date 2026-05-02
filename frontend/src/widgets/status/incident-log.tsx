'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Terminal } from 'lucide-react';
import type { PublicNetworkIncident } from '@/lib/api/public-network';

interface IncidentLogProps {
  incidents: PublicNetworkIncident[];
}

function incidentTone(severity: PublicNetworkIncident['severity']) {
  if (severity === 'critical') return 'text-destructive';
  if (severity === 'major') return 'text-warning';
  return 'text-neon-cyan';
}

export function IncidentLog({ incidents }: IncidentLogProps) {
  const t = useTranslations('Status');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="flex-1 min-h-[250px] border border-white/10 bg-black/60 backdrop-blur-xl rounded-xl flex flex-col overflow-hidden relative"
    >
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[linear-gradient(transparent_50%,rgba(0,255,255,1)_50%)] bg-[length:100%_4px]" />

      <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-neon-cyan" />
          <h3 className="font-mono text-xs text-white uppercase tracking-widest">
            {t('incidents.title')}
          </h3>
        </div>
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full bg-white/20" />
          <div className="w-2 h-2 rounded-full bg-white/20" />
          <div className="w-2 h-2 rounded-full bg-neon-cyan animate-pulse" />
        </div>
      </div>

      <div className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-3 relative z-10 custom-scrollbar">
        {incidents.length > 0 ? (
          incidents.map((incident) => (
            <div key={incident.id} className="flex gap-4 group">
              <span className="text-white/30 shrink-0">
                [{new Date(incident.startedAt).toISOString().slice(11, 19)}Z]
              </span>
              <span className={`shrink-0 ${incidentTone(incident.severity)}`}>
                [{incident.severity.toUpperCase()}]
              </span>
              <span className="text-white/70 group-hover:text-white transition-colors">
                {incident.publicSummary}
              </span>
            </div>
          ))
        ) : (
          <div className="h-full flex items-center justify-center text-white/30 italic">
            {t('incidents.empty')}
          </div>
        )}
      </div>

      <div className="p-3 border-t border-white/5 text-center bg-white/[0.01]">
        <span className="font-mono text-[10px] text-white/50 uppercase tracking-widest">
          [ {t('incidents.view_all')} ]
        </span>
      </div>
    </motion.div>
  );
}
