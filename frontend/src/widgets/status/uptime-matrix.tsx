'use client';

import { useTranslations } from 'next-intl';
import { useMemo } from 'react';
import { motion } from 'motion/react';
import { Database } from 'lucide-react';

interface UptimeDay {
    date: string;
    status: 'nominal' | 'warning' | 'outage' | 'maintenance';
}

function generateHistoryData(): UptimeDay[] {
    const data: UptimeDay[] = [];
    const today = new Date();
    
    // Generate 90 days backwards
    for (let i = 89; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        
        // Randomly simulate outages/warnings
        const rand = Math.random();
        let status: UptimeDay['status'] = 'nominal';
        if (rand > 0.98) status = 'outage';
        else if (rand > 0.95) status = 'warning';
        else if (rand > 0.92) status = 'maintenance';
        
        data.push({
            date: d.toISOString().split('T')[0],
            status
        });
    }
    return data;
}

export function UptimeMatrix() {
    const t = useTranslations('Status');
    const data = useMemo(() => generateHistoryData(), []);
    
    const getColorClass = (status: UptimeDay['status']) => {
        switch(status) {
            case 'nominal': return 'bg-matrix-green hover:shadow-[0_0_10px_#00ff88]';
            case 'warning': return 'bg-warning hover:shadow-[0_0_10px_#ffb800]';
            case 'outage': return 'bg-destructive animate-pulse hover:shadow-[0_0_15px_#ff0055]';
            case 'maintenance': return 'bg-neon-cyan hover:shadow-[0_0_10px_#00ffff]';
        }
    };

    return (
        <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="w-full border border-white/10 bg-black/60 backdrop-blur-xl rounded-xl p-4 md:p-6"
        >
            <div className="flex justify-between items-end mb-6">
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
                
                {/* Legend */}
                <div className="hidden md:flex gap-4 font-mono text-[10px] text-muted-foreground-low uppercase">
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-sm bg-matrix-green" /> Nominal</div>
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-sm bg-warning" /> Warning</div>
                    <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-sm bg-destructive" /> Outage</div>
                </div>
            </div>

            {/* Grid Container */}
            <div className="w-full overflow-x-auto custom-scrollbar pb-2">
                <div className="flex gap-1 min-w-max">
                    {data.map((day, i) => (
                        <div 
                            key={i}
                            className={`w-3 h-10 rounded-sm transition-all duration-300 cursor-crosshair group relative ${getColorClass(day.status)}`}
                        >
                            {/* Tooltip */}
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max px-2 py-1 bg-black border border-white/20 rounded-md opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none">
                                <p className="font-mono text-[10px] text-white">
                                    {day.date} <br/> 
                                    <span className={
                                        day.status === 'outage' ? 'text-destructive' : 
                                        day.status === 'warning' ? 'text-warning' : 
                                        day.status === 'maintenance' ? 'text-neon-cyan' : 'text-matrix-green'
                                    }>
                                        [{day.status.toUpperCase()}]
                                    </span>
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
        </motion.div>
    );
}
