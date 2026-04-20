'use client';

import { useTranslations } from 'next-intl';
import { Activity, Cpu, Wifi } from 'lucide-react';
import { motion } from 'motion/react';
import { useState, useEffect } from 'react';

// A small sparkline component for decorative metrics
function Sparkline({ data, color }: { data: number[], color: string }) {
    const max = Math.max(...data, 100);
    const min = Math.min(...data, 0);
    const range = max - min;
    
    // Convert data to SVG path
    const points = data.map((val, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = 100 - ((val - min) / range) * 100;
        return `${x},${y}`;
    }).join(' ');

    return (
        <svg viewBox="0 0 100 100" className="w-full h-8 preserve-3d" preserveAspectRatio="none">
            <polyline 
                points={points} 
                fill="none" 
                stroke={color} 
                strokeWidth="2" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                className="opacity-80"
            />
            {/* Soft glow under the line */}
            <polyline 
                points={`0,100 ${points} 100,100`} 
                fill={color} 
                stroke="none" 
                className="opacity-10"
            />
        </svg>
    );
}

export function MetricsHUD() {
    const t = useTranslations('Status');
    
    // Mock oscillating data
    const [bandwidth, setBandwidth] = useState<number[]>(Array(20).fill(50));
    const [cpu, setCpu] = useState<number[]>(Array(20).fill(30));
    const [latency, setLatency] = useState<number[]>(Array(20).fill(25));

    useEffect(() => {
        const interval = setInterval(() => {
            setBandwidth(prev => [...prev.slice(1), 60 + Math.random() * 40]);
            setCpu(prev => [...prev.slice(1), 20 + Math.random() * 25]);
            setLatency(prev => [...prev.slice(1), 24 + Math.random() * 5]);
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const metrics = [
        { label: t('metrics.bandwidth'), value: '42.8 Tbps', icon: Wifi, data: bandwidth, color: '#00ffff' },
        { label: t('metrics.active_nodes'), value: '1,492', icon: Cpu, data: cpu, color: '#00ff88' },
        { label: t('metrics.latency'), value: '25ms', icon: Activity, data: latency, color: '#ffb800' },
    ];

    return (
        <div className="grid gap-4">
            {metrics.map((m, i) => {
                const Icon = m.icon;
                return (
                    <motion.div 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        key={m.label} 
                        className="p-4 border border-white/10 bg-black/40 backdrop-blur-md rounded-xl relative overflow-hidden group"
                    >
                        {/* Hover glow */}
                        <div 
                            className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500"
                            style={{ background: `radial-gradient(circle at right center, ${m.color}, transparent 70%)` }}
                        />
                        
                        <div className="flex justify-between items-start mb-4 relative z-10">
                            <div>
                                <p className="text-[10px] font-mono text-muted-foreground-low uppercase tracking-wider mb-1">
                                    {m.label}
                                </p>
                                <p className="text-2xl font-display font-bold text-white tracking-widest">
                                    {m.value}
                                </p>
                            </div>
                            <div className="p-2 bg-white/5 rounded-lg border border-white/5">
                                <Icon className="w-4 h-4" style={{ color: m.color }} />
                            </div>
                        </div>
                        
                        <div className="relative z-10">
                            <Sparkline data={m.data} color={m.color} />
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
