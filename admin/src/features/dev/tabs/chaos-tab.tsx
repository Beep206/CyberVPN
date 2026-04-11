import React, { useState, useEffect, useRef } from 'react';
import { Skull, AlertTriangle, Clock, Zap, Ghost, Layout } from 'lucide-react';
import { cn } from '@/lib/utils';
import { networkLogger } from '../lib/network-logger';

export function ChaosTab({ isDark }: { isDark: boolean }) {
    const [latency, setLatency] = useState(networkLogger.chaosLatency);
    const [failureRate, setFailureRate] = useState(networkLogger.chaosFailureRate);
    const [throwError, setThrowError] = useState(false);

    const [gremlinActive, setGremlinActive] = useState(false);
    const [gremlinStats, setGremlinStats] = useState({ clicks: 0, errors: 0 });
    const [clsActive, setClsActive] = useState(false);

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

    // Gremlin Auto-Fuzzer
    useEffect(() => {
        if (!gremlinActive) return;
        
        const interval = setInterval(() => {
            const x = Math.floor(Math.random() * window.innerWidth);
            const y = Math.floor(Math.random() * window.innerHeight);
            const el = document.elementFromPoint(x, y);
            
            // Prevent clicking inside Dev Panel
            if (el && !el.closest('#dev-panel-root')) {
                const event = new MouseEvent('click', { view: window, bubbles: true, cancelable: true });
                el.dispatchEvent(event);
                setGremlinStats(s => ({ ...s, clicks: s.clicks + 1 }));
            }
        }, 80); // ~12 clicks per second

        const handleErr = () => setGremlinStats(s => ({ ...s, errors: s.errors + 1 }));
        window.addEventListener('error', handleErr);
        window.addEventListener('unhandledrejection', handleErr);
        
        return () => {
            clearInterval(interval);
            window.removeEventListener('error', handleErr);
            window.removeEventListener('unhandledrejection', handleErr);
        };
    }, [gremlinActive]);

    // Cumulative Layout Shift (CLS) Detector
    useEffect(() => {
        if (!clsActive || typeof PerformanceObserver === 'undefined') return;

        let observer: PerformanceObserver | null = null;
        try {
            observer = new PerformanceObserver((list) => {
                list.getEntries().forEach((entry: any) => {
                    if (!entry.hadRecentInput && entry.sources) {
                        entry.sources.forEach((source: any) => {
                            const node = source.node;
                            if (node && node.nodeType === 1 && !node.closest('#dev-panel-root')) {
                                const el = node as HTMLElement;
                                const prevOut = el.style.outline;
                                const prevOutOff = el.style.outlineOffset;
                                const prevTrans = el.style.transition;
                                
                                el.style.transition = 'outline 0.1s, outline-offset 0.1s';
                                el.style.outline = '4px dashed red';
                                el.style.outlineOffset = '2px';
                                
                                setTimeout(() => {
                                    el.style.outline = prevOut;
                                    el.style.outlineOffset = prevOutOff;
                                    setTimeout(() => el.style.transition = prevTrans, 100);
                                }, 800);
                            }
                        });
                    }
                });
            });
            observer.observe({ type: 'layout-shift', buffered: true });
        } catch (e) {
            console.warn("CLS observation not supported");
        }

        return () => {
            if (observer) observer.disconnect();
        };
    }, [clsActive]);

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

            <div className="grid grid-cols-2 gap-4">
                {/* Gremlin Auto-Fuzzer */}
                <div className={cn("p-4 border rounded flex flex-col justify-between", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-green-400" : "text-green-600")}>
                            <Ghost className="w-4 h-4" /> Gremlin Fuzzer
                        </h4>
                        <p className={cn("text-[10px] mb-4", isDark ? "text-gray-500" : "text-slate-500")}>
                            Spawns invisible bots that randomly click the DOM 12 times a second.
                        </p>
                    </div>
                    
                    <button
                        onClick={() => {
                            if (!gremlinActive) setGremlinStats({ clicks: 0, errors: 0 });
                            setGremlinActive(!gremlinActive);
                        }}
                        className={cn(
                            "w-full py-2 text-xs font-bold rounded uppercase tracking-widest transition-colors mb-2 border",
                            gremlinActive
                                ? (isDark ? "bg-green-500/20 text-green-300 border-green-500 shadow-[0_0_10px_rgba(34,197,94,0.4)]" : "bg-green-100 text-green-700 border-green-500")
                                : (isDark ? "bg-gray-900 border-gray-700 text-gray-400 hover:border-green-500/50 hover:text-green-400" : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100")
                        )}
                    >
                        {gremlinActive ? "Fuzzing Active" : "Start Fuzzing"}
                    </button>
                    
                    <div className="flex justify-between text-[10px] font-mono px-1">
                        <span className={isDark ? "text-gray-400" : "text-slate-500"}>Clicks: <b className={isDark ? "text-white" : "text-black"}>{gremlinStats.clicks}</b></span>
                        <span className={isDark ? "text-red-400" : "text-red-600"}>Errors: <b>{gremlinStats.errors}</b></span>
                    </div>
                </div>

                {/* CLS Detector */}
                <div className={cn("p-4 border rounded flex flex-col justify-between", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-blue-400" : "text-blue-600")}>
                            <Layout className="w-4 h-4" /> CLS Detector
                        </h4>
                        <p className={cn("text-[10px] mb-4", isDark ? "text-gray-500" : "text-slate-500")}>
                            Highlights elements with a red dashed border when they unexpectedly shift layout without user input.
                        </p>
                    </div>
                    
                    <button
                        onClick={() => setClsActive(!clsActive)}
                        className={cn(
                            "w-full py-2 text-xs font-bold rounded uppercase tracking-widest transition-colors border",
                            clsActive
                                ? (isDark ? "bg-blue-500/20 text-blue-300 border-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.4)]" : "bg-blue-100 text-blue-700 border-blue-500")
                                : (isDark ? "bg-gray-900 border-gray-700 text-gray-400 hover:border-blue-500/50 hover:text-blue-400" : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100")
                        )}
                    >
                        {clsActive ? "Observing Shifts" : "Detect Layout Shifts"}
                    </button>
                </div>
            </div>
        </div>
    );
}
