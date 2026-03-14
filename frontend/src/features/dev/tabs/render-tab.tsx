import React, { useState, useEffect } from 'react';
import { Activity, Zap, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import { renderProfiler } from '../lib/render-profiler';

export function RenderTab({ isDark }: { isDark: boolean }) {
    const [paintFlashing, setPaintFlashing] = useState(false);

    // Sync from local storage/singleton on mount
    useEffect(() => {
        setPaintFlashing(renderProfiler.isFlashing);
    }, []);

    const togglePaintFlashing = () => {
        const next = !paintFlashing;
        setPaintFlashing(next);
        renderProfiler.toggle(next);
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.8)]" : "text-yellow-600")}>
                    <Activity className="w-5 h-5 text-yellow-500" /> Render Profiler
                </h3>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                Visualizes DOM updates and layout shifts in real-time. Useful for tracking down unnecessary re-renders in heavy components like tables and graphs.
            </p>

            <div className={cn("p-4 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-yellow-400" : "text-yellow-600")}>
                            <Zap className="w-4 h-4" /> Paint Flashing
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Highlights elements with colorful bounding boxes whenever they mutate or repaint.</p>
                    </div>
                    <button
                        onClick={togglePaintFlashing}
                        className={cn(
                            "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                            paintFlashing
                                ? (isDark ? "bg-yellow-500/30 border-yellow-500 shadow-[0_0_15px_rgba(234,179,8,0.4)]" : "bg-yellow-100 border-yellow-500")
                                : (isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")
                        )}
                    >
                        <div
                            className={cn(
                                "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                                paintFlashing
                                    ? (isDark ? "translate-x-6 bg-yellow-400 shadow-[0_0_10px_#facc15]" : "translate-x-6 bg-yellow-500")
                                    : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                            )}
                        />
                    </button>
                </div>
            </div>

            <div className={cn("p-4 border rounded opacity-50 relative overflow-hidden", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(0,0,0,0.1)_10px,rgba(0,0,0,0.1)_20px)] pointer-events-none z-10" />
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-blue-400" : "text-blue-600")}>
                            <Layers className="w-4 h-4" /> Layout Shift Regions (WIP)
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Highlights Cumulative Layout Shifts (CLS) in blue. Currently in development.</p>
                    </div>
                </div>
            </div>

        </div>
    );
}
