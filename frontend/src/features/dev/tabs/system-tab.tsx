import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Activity, HardDrive, Cpu, AlertTriangle } from 'lucide-react';

export function SystemTab({ isDark }: { isDark: boolean }) {
    const [memHistory, setMemHistory] = useState<number[]>(Array(30).fill(0));
    const [currentMem, setCurrentMem] = useState<number>(0);
    const [memLimit, setMemLimit] = useState<number>(0);

    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;
        if (typeof window !== 'undefined' && (performance as any).memory) {
            setMemLimit((performance as any).memory.jsHeapSizeLimit);
            interval = setInterval(() => {
                const used = (performance as any).memory.usedJSHeapSize;
                setCurrentMem(used);
                setMemHistory(prev => [...prev.slice(1), used]);
            }, 1000);
        }
        return () => clearInterval(interval);
    }, []);

    const formatMB = (bytes: number) => (bytes / 1024 / 1024).toFixed(1);

    // Calculate chart points (0 to 1 scaling, inverted Y for SVG)
    const maxHist = Math.max(...memHistory, 1);
    const minHist = Math.min(...memHistory.filter(x => x > 0), maxHist * 0.5); // Provide baseline
    const range = maxHist - minHist || 1;
    
    const points = memHistory.map((val, i) => {
        const x = (i / (memHistory.length - 1)) * 100;
        const y = 100 - (((val - minHist) / range) * 100);
        return `${x},${Math.max(0, Math.min(100, y))}`;
    }).join(' ');

    const leakWarning = currentMem > (memLimit * 0.8) && memLimit > 0;

    return (
        <div className="space-y-4 relative z-20 h-full flex flex-col">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-2 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>System & Performance</h3>

            {/* Memory JS Heap Leak Detector */}
            <div className={cn("p-4 border rounded flex flex-col", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex justify-between items-start mb-2">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-purple-400" : "text-purple-600")}>
                            <Cpu className="w-4 h-4" /> JS Heap Size
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Monitors `performance.memory` to detect frontend memory leaks.</p>
                    </div>
                </div>

                {(performance as any).memory ? (
                    <div className="mt-2">
                        <div className="flex justify-between items-end mb-1">
                            <span className={cn("text-2xl font-black font-mono tracking-tighter", leakWarning ? "text-red-500" : (isDark ? "text-purple-300" : "text-purple-700"))}>
                                {formatMB(currentMem)} <span className="text-sm opacity-50">MB</span>
                            </span>
                            <span className={cn("text-[10px] font-mono", isDark ? "text-gray-500" : "text-slate-400")}>
                                Limit: {formatMB(memLimit)} MB
                            </span>
                        </div>
                        
                        <div className={cn("w-full h-16 border rounded relative overflow-hidden", isDark ? "bg-black border-gray-800" : "bg-slate-50 border-slate-200")}>
                            {/* Grid lines */}
                            <div className="absolute inset-0 border-b border-dashed border-purple-500/20 top-1/2"></div>
                             
                             {/* SVG Sparkline */}
                            <svg preserveAspectRatio="none" className="w-full h-full absolute inset-0 text-purple-500 overflow-visible z-10" viewBox="0 0 100 100">
                                <linearGradient id="memFade" x1="0" x2="0" y1="0" y2="1">
                                    <stop offset="0%" stopColor="currentColor" stopOpacity="0.5" />
                                    <stop offset="100%" stopColor="currentColor" stopOpacity="0.0" />
                                </linearGradient>
                                <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                                <polygon points={`0,100 ${points} 100,100`} fill="url(#memFade)" />
                            </svg>
                        </div>
                        
                        {leakWarning && (
                            <div className="mt-2 text-[10px] font-bold text-red-500 flex items-center gap-1 bg-red-500/10 p-1.5 rounded border border-red-500/20">
                                <AlertTriangle className="w-3 h-3" /> Critical memory threshold reached. Hard refresh recommended.
                            </div>
                        )}
                    </div>
                ) : (
                    <div className={cn("p-4 text-center italic text-xs border rounded border-dashed mt-2", isDark ? "border-gray-800 text-gray-500" : "border-slate-300 text-slate-400")}>
                        performance.memory API is not supported in this browser. Try Chrome/Edge.
                    </div>
                )}
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono mt-auto">
                <div className={cn("p-3 border rounded transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>NODE_ENV</span>
                    <span className={cn("font-black text-sm tracking-wide", isDark ? "text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]" : "text-slate-800")}>{process.env.NODE_ENV}</span>
                </div>
                <div className={cn("p-3 border rounded transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>Platform</span>
                    <span className={cn("font-black text-sm tracking-wide", isDark ? "text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]" : "text-slate-800")}>{typeof window !== 'undefined' ? window.navigator.platform : 'Server'}</span>
                </div>
                <div className={cn("p-3 border rounded col-span-2 transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>User Agent</span>
                    <span className={cn("break-all font-semibold transition-colors", isDark ? "text-gray-100 group-hover:text-neon-cyan" : "text-slate-700")}>{typeof window !== 'undefined' ? window.navigator.userAgent : 'Server'}</span>
                </div>
            </div>
        </div>
    );
}
