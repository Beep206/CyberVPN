import React, { useState, useEffect } from 'react';
import { Skull, AlertTriangle, Clock, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { networkLogger } from '../lib/network-logger';

export function ChaosTab({ isDark }: { isDark: boolean }) {
    const [latency, setLatency] = useState(networkLogger.chaosLatency);
    const [failureRate, setFailureRate] = useState(networkLogger.chaosFailureRate);
    const [throwError, setThrowError] = useState(false);

    // On mount, read initial
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const l = parseInt(localStorage.getItem('DEV_CHAOS_LATENCY') || '0', 10);
            const f = parseInt(localStorage.getItem('DEV_CHAOS_FAILURE') || '0', 10);
            if (!isNaN(l)) {
                setLatency(l);
                networkLogger.chaosLatency = l;
            }
            if (!isNaN(f)) {
                setFailureRate(f);
                networkLogger.chaosFailureRate = f;
            }
        }
    }, []);

    useEffect(() => {
        networkLogger.chaosLatency = latency;
        if (typeof window !== 'undefined') localStorage.setItem('DEV_CHAOS_LATENCY', String(latency));
    }, [latency]);

    useEffect(() => {
        networkLogger.chaosFailureRate = failureRate;
        if (typeof window !== 'undefined') localStorage.setItem('DEV_CHAOS_FAILURE', String(failureRate));
    }, [failureRate]);

    if (throwError) {
        throw new Error("Synthetic Chaos Error triggered from Dev Panel");
    }

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500 drop-shadow-[0_0_8px_rgba(255,0,0,0.8)]" : "text-red-700")}>
                    <Skull className="w-5 h-5 text-red-500" /> Chaos Simulator
                </h3>
            </div>

            <div className={cn("p-4 border rounded", isDark ? "bg-red-950/20 border-red-900/50" : "bg-red-50 border-red-200")}>
                <h4 className={cn("font-bold flex items-center gap-2 mb-2", isDark ? "text-red-400" : "text-red-600")}>
                    <AlertTriangle className="w-4 h-4" /> Trigger Error Boundary
                </h4>
                <p className={cn("text-xs mb-4", isDark ? "text-red-200/50" : "text-red-500/80")}>Force a React render error to test the closest Error Boundary component.</p>
                <button
                    onClick={() => setThrowError(true)}
                    className="w-full py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded uppercase tracking-widest transition-colors shadow-[0_0_15px_rgba(255,0,0,0.3)]"
                >
                    Throw JS Error
                </button>
            </div>

            <div className={cn("p-4 border rounded space-y-4", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-orange-400" : "text-orange-600")}>
                        <Clock className="w-4 h-4" /> API Latency Addition
                    </h4>
                    <p className={cn("text-[10px] mb-3", isDark ? "text-gray-500" : "text-slate-500")}>Add artificial delay (+ms) to all outgoing fetch and XHR requests.</p>
                    
                    <div className="flex items-center gap-4">
                        <input 
                            type="range" 
                            min="0" max="5000" step="100" 
                            value={latency} 
                            onChange={(e) => setLatency(Number(e.target.value))}
                            className="flex-1 accent-orange-500" 
                        />
                        <span className={cn("font-mono text-xs w-12 text-right", isDark ? "text-orange-300" : "text-orange-700")}>{latency}ms</span>
                    </div>
                </div>

                <div className="pt-4 border-t border-dashed border-gray-500/30">
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-yellow-400" : "text-yellow-600")}>
                        <Zap className="w-4 h-4" /> API Failure Rate
                    </h4>
                    <p className={cn("text-[10px] mb-3", isDark ? "text-gray-500" : "text-slate-500")}>Percentage of requests that will randomly fail with a 500 error.</p>
                    
                    <div className="flex items-center gap-4">
                        <input 
                            type="range" 
                            min="0" max="100" step="5" 
                            value={failureRate} 
                            onChange={(e) => setFailureRate(Number(e.target.value))}
                            className="flex-1 accent-yellow-500" 
                        />
                        <span className={cn("font-mono text-xs w-12 text-right", isDark ? "text-yellow-300" : "text-yellow-700")}>{failureRate}%</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
