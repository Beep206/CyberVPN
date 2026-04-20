'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Activity, ShieldAlert, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type ThreatEvent = {
    id: number;
    type: 'blocked' | 'deflected';
    messageKey: string;
    ip: string;
    time: string;
};

const IPS = ['192.168.x.x', '45.76.x.x', '23.111.x.x', '88.198.x.x', '104.21.x.x', '9.9.9.x'];
const EVENTS = ['dpi', 'syn', 'brute', 'malware', 'tracker'];

function generateThreatEvent(id: number): ThreatEvent {
    const type = Math.random() > 0.5 ? 'blocked' : 'deflected';
    const messageKey = EVENTS[Math.floor(Math.random() * EVENTS.length)];
    const ip = IPS[Math.floor(Math.random() * IPS.length)];
    const date = new Date();
    const time = `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;

    return { id, type, messageKey, ip, time };
}

function createInitialThreatLogs(count: number): ThreatEvent[] {
    return Array.from({ length: count }, (_, index) => generateThreatEvent(index));
}

export function ThreatRadar() {
    const t = useTranslations('Security.radar');
    const [logs, setLogs] = useState<ThreatEvent[]>(() => createInitialThreatLogs(5));
    const nextEventIdRef = useRef(logs.length);

    useEffect(() => {
        const interval = window.setInterval(() => {
            setLogs(prev => {
                const newLogs = [generateThreatEvent(nextEventIdRef.current), ...prev];
                nextEventIdRef.current += 1;
                if (newLogs.length > 8) newLogs.pop(); // Keep only last 8 events
                return newLogs;
            });
        }, 3000); // New event every 3 seconds

        return () => window.clearInterval(interval);
    }, []);

    return (
        <div className="w-[380px] h-[400px] border border-grid-line/50 bg-black/80 backdrop-blur-md rounded-xl overflow-hidden flex flex-col font-mono relative">
            
            {/* Ambient terminal glow */}
            <div className="absolute inset-0 bg-neon-cyan/5 mix-blend-screen pointer-events-none" />
            <div
                className="absolute inset-0 opacity-10 pointer-events-none"
                style={{ backgroundImage: "url('/scanlines.png')" }}
            />

            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-grid-line/50 bg-terminal-bg relative z-10">
                <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-neon-cyan animate-pulse" />
                    <span className="text-xs text-white/80 font-bold tracking-wider">{t('title')}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                    <span className="text-[10px] text-warning uppercase">{t('status')}</span>
                </div>
            </div>

            {/* Live Feed Container */}
            <div className="flex-1 p-4 overflow-hidden relative z-10 flex flex-col justify-end">
                <AnimatePresence initial={false}>
                    {logs.map((log) => (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0, x: 20, height: 0 }}
                            animate={{ opacity: 1, x: 0, height: 'auto' }}
                            exit={{ opacity: 0, scale: 0.9, height: 0 }}
                            transition={{ duration: 0.3 }}
                            className="text-xs mb-3 font-mono flex flex-col gap-1 border-l-2 pl-3 py-1"
                            style={{ 
                                borderColor: log.type === 'blocked' ? '#ff0055' : '#00ff88',
                                backgroundColor: log.type === 'blocked' ? 'rgba(255,0,85,0.05)' : 'rgba(0,255,136,0.05)'
                            }}
                        >
                            <div className="flex items-center justify-between text-[10px] text-muted-foreground opacity-70">
                                <span>[{log.time}] SRC: <span className="text-white/60">{log.ip}</span></span>
                                {log.type === 'blocked' ? (
                                    <span className="text-red-500 font-bold flex items-center gap-1"><ShieldAlert className="w-3 h-3"/> {t('blocked')}</span>
                                ) : (
                                    <span className="text-matrix-green font-bold flex items-center gap-1"><ShieldCheck className="w-3 h-3"/> {t('deflected')}</span>
                                )}
                            </div>
                            <span className="text-white/80 leading-relaxed">
                                {t(`events.${log.messageKey}`)}
                            </span>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
        </div>
    );
}
