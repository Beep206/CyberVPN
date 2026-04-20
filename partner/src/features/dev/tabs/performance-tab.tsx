import { useState, useEffect, useRef } from "react";
import { Monitor, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

export function PerformanceTab({ isDark }: { isDark: boolean }) {
    const [fps, setFps] = useState<number>(0);
    const [ping, setPing] = useState<number>(0);
    const [memory, setMemory] = useState<{ used: string, total: string } | null>(null);
    const [connection, setConnection] = useState<string>('Unknown');
    const rafRef = useRef<number | null>(null);
    const frameCountRef = useRef(0);
    const lastTimeRef = useRef(0);

    /* eslint-disable react-hooks/set-state-in-effect -- Performance tab monitoring */
    useEffect(() => {
        if (typeof window === "undefined") return;

        let active = true;
        lastTimeRef.current = performance.now();

        // FPS Monitor
        const countFrame = () => {
            if (!active) return;
            frameCountRef.current++;
            rafRef.current = requestAnimationFrame(countFrame);
        };
        rafRef.current = requestAnimationFrame(countFrame);

        const fpsInterval = setInterval(() => {
            if (!active) return;
            const now = performance.now();
            const delta = now - lastTimeRef.current;
            if (delta > 0) {
                setFps(Math.round((frameCountRef.current * 1000) / delta));
            }
            frameCountRef.current = 0;
            lastTimeRef.current = now;
        }, 1000);

        return () => {
            active = false;
            if (rafRef.current) cancelAnimationFrame(rafRef.current);
            clearInterval(fpsInterval);
        };
    }, []);

    useEffect(() => {
        if (typeof window === "undefined") return;

        let active = true;
        // Ping & Network Monitor
        const measureMetrics = async () => {
            if (!active) return;
            
            // Measure Ping
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            const start = performance.now();
            try {
                await fetch('/favicon.ico', { method: 'HEAD', cache: 'no-store', signal: controller.signal });
            } catch { /* ignore */ }
            clearTimeout(timeoutId);
            const duration = Math.round(performance.now() - start);
            
            if (active) {
                setPing(duration);
                
                // Track memory
                if ('memory' in performance) {
                    const mem = (performance as unknown as { memory: { usedJSHeapSize: number, jsHeapSizeLimit: number } }).memory;
                    setMemory({
                        used: (mem.usedJSHeapSize / 1048576).toFixed(1),
                        total: (mem.jsHeapSizeLimit / 1048576).toFixed(1)
                    });
                }

                // Track connection
                if ('connection' in navigator) {
                    const conn = (navigator as unknown as { connection: { effectiveType?: string, downlink?: number } }).connection;
                    setConnection(`${conn.effectiveType?.toUpperCase()} (${conn.downlink}Mbps)`);
                }
            }
        };

        measureMetrics();
        const interval = setInterval(measureMetrics, 3000);
        return () => {
            active = false;
            clearInterval(interval);
        };
    }, []);
    /* eslint-enable react-hooks/set-state-in-effect */

    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Live Metrics</h3>

            {/* FPS & Ping */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className={cn("flex flex-col items-center justify-center p-4 border rounded group transition-all", isDark ? "bg-black border-neon-cyan/30 shadow-[0_0_15px_rgba(0,255,255,0.1)]" : "bg-white border-blue-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-2 uppercase text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>Framerate</span>
                    <span className={cn("font-black text-3xl font-display", isDark ? "text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,0.8)]" : "text-blue-600")}>{fps || '--'}</span>
                    <span className={cn("text-[9px] mt-1", isDark ? "text-gray-500" : "text-slate-400")}>FPS</span>
                </div>
                <div className={cn("flex flex-col items-center justify-center p-4 border rounded group transition-all", isDark ? "bg-black border-matrix-green/30 shadow-[0_0_15px_rgba(0,255,0,0.1)]" : "bg-white border-emerald-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-2 uppercase text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>Latency</span>
                    <span className={cn("font-black text-3xl font-display", isDark ? "text-matrix-green drop-shadow-[0_0_10px_rgba(0,255,0,0.8)]" : "text-emerald-600")}>{ping || '--'}</span>
                    <span className={cn("text-[9px] mt-1", isDark ? "text-gray-500" : "text-slate-400")}>ms</span>
                </div>
            </div>

            {/* Memory & Network */}
            <div className="grid gap-3">
                <div className={cn("flex items-center gap-3 p-3 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                    <div className={cn("p-2 rounded", isDark ? "bg-neon-cyan/10" : "bg-blue-50")}>
                        <Monitor className={cn("w-4 h-4", isDark ? "text-neon-cyan" : "text-blue-500")} />
                    </div>
                    <div className="flex-1">
                        <div className="flex justify-between items-center mb-1">
                            <span className={cn("text-[10px] uppercase font-bold", isDark ? "text-gray-400" : "text-slate-500")}>Memory Heap</span>
                            <span className={cn("text-xs font-bold", isDark ? "text-white" : "text-slate-800")}>{memory ? `${memory.used} MB` : 'N/A'}</span>
                        </div>
                        <div className={cn("h-1.5 w-full rounded-full overflow-hidden", isDark ? "bg-gray-800" : "bg-slate-100")}>
                            {memory && (
                                <div 
                                    className={cn("h-full transition-all duration-1000", isDark ? "bg-neon-cyan shadow-[0_0_5px_#00ffff]" : "bg-blue-500")} 
                                    style={{ width: `${(parseFloat(memory.used) / parseFloat(memory.total)) * 100}%` }}
                                />
                            )}
                        </div>
                    </div>
                </div>

                <div className={cn("flex items-center gap-3 p-3 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                    <div className={cn("p-2 rounded", isDark ? "bg-matrix-green/10" : "bg-emerald-50")}>
                        <Globe className={cn("w-4 h-4", isDark ? "text-matrix-green" : "text-emerald-500")} />
                    </div>
                    <div className="flex-1">
                        <span className={cn("text-[10px] uppercase font-bold block mb-0.5", isDark ? "text-gray-400" : "text-slate-500")}>Network Uplink</span>
                        <span className={cn("text-xs font-bold block", isDark ? "text-white" : "text-slate-800")}>{connection}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
