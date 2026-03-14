import React, { useState, useEffect } from 'react';
import { Layers, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { cssXRay } from '../lib/css-xray';

export function XRayTab({ isDark }: { isDark: boolean }) {
    const [xrayActive, setXrayActive] = useState(false);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            setXrayActive(cssXRay.isActive);
        }
    }, []);

    const toggleXRay = () => {
        const next = !xrayActive;
        setXrayActive(next);
        cssXRay.toggle(next);
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2 shrink-0">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]" : "text-cyan-600")}>
                    <Layers className="w-5 h-5 text-cyan-500" /> CSS X-Ray
                </h3>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                Injects an aggressive universal `outline` CSS rule across the entire DOM. Useful for instantly spotting overflowing containers, massive invisible divs blocking clicks, and margin collapsing issues.
            </p>

            <div className={cn("p-4 border rounded flex items-center justify-between", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-cyan-400" : "text-cyan-600")}>
                        <Zap className="w-4 h-4" /> Global Wireframe Mode
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        {xrayActive ? "X-Ray borders are currently active." : "Normal layout rendering."}
                    </p>
                </div>
                {xrayActive ? (
                    <button onClick={toggleXRay} className={cn("relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2", isDark ? "bg-cyan-500/30 border-cyan-500 shadow-[0_0_15px_rgba(34,211,238,0.4)]" : "bg-cyan-100 border-cyan-500")}>
                         <div className={cn("absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300", isDark ? "translate-x-6 bg-cyan-400 shadow-[0_0_10px_#22d3ee]" : "translate-x-6 bg-cyan-500")} />
                    </button>
                ) : (
                    <button onClick={toggleXRay} className={cn("relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2", isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")}>
                         <div className={cn("absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300", isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")} />
                    </button>
                )}
            </div>
        </div>
    );
}
