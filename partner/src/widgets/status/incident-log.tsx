'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Terminal } from 'lucide-react';

const mockIncidents = [
    { time: '14:23:01Z', level: 'INFO', msg: 'Node AP-04 (Tokyo) automated scaling event.' },
    { time: '13:45:12Z', level: 'WARN', msg: 'Slight latency increase detected in EU-West backbone. Traffic rerouted.' },
    { time: '10:02:44Z', level: 'INFO', msg: 'Daily cryptographic key rotation complete.' },
    { time: '08:15:00Z', level: 'INFO', msg: 'System wide telemetry snapshot archived.' },
];

export function IncidentLog() {
    const t = useTranslations('Status');

    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex-1 min-h-[250px] border border-white/10 bg-black/60 backdrop-blur-xl rounded-xl flex flex-col overflow-hidden relative"
        >
            {/* Scanline decoration */}
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
                {mockIncidents.length > 0 ? (
                    mockIncidents.map((incident, i) => (
                        <div key={i} className="flex gap-4 group">
                            <span className="text-white/30 shrink-0">[{incident.time}]</span>
                            <span className={`shrink-0 ${incident.level === 'WARN' ? 'text-warning' : 'text-neon-cyan'}`}>
                                [{incident.level}]
                            </span>
                            <span className="text-white/70 group-hover:text-white transition-colors">
                                {incident.msg}
                            </span>
                        </div>
                    ))
                ) : (
                    <div className="h-full flex items-center justify-center text-white/30 italic">
                        {t('incidents.empty')}
                    </div>
                )}
            </div>
            
            <div className="p-3 border-t border-white/5 text-center bg-white/[0.01] hover:bg-white/[0.03] transition-colors cursor-pointer group">
                <span className="font-mono text-[10px] text-white/50 group-hover:text-neon-cyan transition-colors uppercase tracking-widest">
                    [ {t('incidents.view_all')} ]
                </span>
            </div>
        </motion.div>
    );
}
