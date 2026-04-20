import React, { useState, useEffect } from 'react';
import { Layers, Zap, Cuboid } from 'lucide-react';
import { cn } from '@/lib/utils';
import { cssXRay } from '../lib/css-xray';

export function XRayTab({ isDark }: { isDark: boolean }) {
    const [xrayActive, setXrayActive] = useState(false);
    const [is3dActive, setIs3dActive] = useState(false);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            setXrayActive(cssXRay.isActive);
        }
    }, []);

    // 3D DOM Visualizer
    useEffect(() => {
        if (typeof window === 'undefined') return;

        const styleId = 'dev-panel-3d-styles';
        if (is3dActive) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                body {
                    perspective: 3000px;
                    overflow-x: hidden;
                    background: #111;
                }
                body > *:not(#dev-panel-root) {
                    transform: rotateX(55deg) rotateZ(-35deg) translateZ(-100px) scale(0.6);
                    transform-style: preserve-3d;
                    transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                    transform-origin: 50% 0%;
                }
                body > *:not(#dev-panel-root) * {
                    transform-style: preserve-3d;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    transform: translateZ(15px);
                    box-shadow: -1px 1px 0px rgba(0,255,255,0.2), 0 0 1px rgba(0,0,0,0.5);
                    background-color: rgba(10, 20, 30, 0.4);
                }
                body > *:not(#dev-panel-root) *:hover {
                    transform: translateZ(40px);
                    box-shadow: -5px 5px 15px rgba(255,0,255,0.4), inset 0 0 10px rgba(0,255,255,0.2);
                    background-color: rgba(255, 0, 255, 0.1);
                    outline: 2px solid cyan;
                }
                /* Exclude the dev panel from 3D scaling entirely */
                #dev-panel-root, #dev-panel-root * {
                    transform: none !important;
                    perspective: none !important;
                    transform-style: flat !important;
                    box-shadow: none !important;
                    background-color: transparent;
                }
            `;
            document.head.appendChild(style);
        } else {
            const style = document.getElementById(styleId);
            if (style) style.remove();
        }

        return () => {
            const style = document.getElementById(styleId);
            if (style) style.remove();
        };
    }, [is3dActive]);

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

            <div className={cn("p-4 border rounded flex items-center justify-between", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-purple-400" : "text-purple-600")}>
                        <Cuboid className="w-4 h-4" /> 3D DOM Layer Visualizer
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        {is3dActive ? "DOM rendered in 3D Perspective." : "Transforms the entire body using 3D perspectives to visualize z-index stacking."}
                    </p>
                </div>
                {is3dActive ? (
                    <button onClick={() => setIs3dActive(false)} className={cn("relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2", isDark ? "bg-purple-500/30 border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.4)]" : "bg-purple-100 border-purple-500")}>
                         <div className={cn("absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300", isDark ? "translate-x-6 bg-purple-400 shadow-[0_0_10px_#c084fc]" : "translate-x-6 bg-purple-500")} />
                    </button>
                ) : (
                    <button onClick={() => setIs3dActive(true)} className={cn("relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2", isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")}>
                         <div className={cn("absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300", isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")} />
                    </button>
                )}
            </div>
        </div>
    );
}
