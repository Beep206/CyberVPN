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

    const [reactFlashActive, setReactFlashActive] = useState(false);

    useEffect(() => {
        if (typeof window === 'undefined') return;

        if (reactFlashActive) {
            const styleId = 'dev-panel-react-flash-style';
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                @keyframes react-render-flash {
                    0% { outline: 2px solid rgba(34, 197, 94, 0.9); box-shadow: inset 0 0 10px rgba(34, 197, 94, 0.3); }
                    100% { outline: 2px solid rgba(34, 197, 94, 0); box-shadow: inset 0 0 0 rgba(34, 197, 94, 0); }
                }
                .dev-react-flash {
                    animation: react-render-flash 0.6s ease-out;
                }
            `;
            document.head.appendChild(style);

            const flashElement = (el: HTMLElement) => {
                if (!el || !el.classList || el.closest('#dev-panel-root')) return;
                el.classList.remove('dev-react-flash');
                void el.offsetWidth; // Force reflow
                el.classList.add('dev-react-flash');
                setTimeout(() => el.classList.remove('dev-react-flash'), 600);
            };

            const observer = new MutationObserver((mutations) => {
                mutations.forEach(m => {
                    if (m.type === 'childList') {
                        m.addedNodes.forEach(n => {
                            if (n.nodeType === 1) flashElement(n as HTMLElement);
                        });
                    } else if (m.type === 'attributes' || m.type === 'characterData') {
                        const target = m.target.nodeType === 3 ? m.target.parentElement : (m.target as HTMLElement);
                        if (target) flashElement(target);
                    }
                });
            });

            observer.observe(document.body, { childList: true, subtree: true, attributes: true, characterData: true });

            return () => {
                observer.disconnect();
                const s = document.getElementById(styleId);
                if (s) s.remove();
                document.querySelectorAll('.dev-react-flash').forEach(el => el.classList.remove('dev-react-flash'));
            };
        }
    }, [reactFlashActive]);

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2 shrink-0">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.8)]" : "text-yellow-600")}>
                    <Activity className="w-5 h-5 text-yellow-500" /> Render Profiler
                </h3>
            </div>

            <p className={cn("text-[10px] shrink-0", isDark ? "text-gray-400" : "text-slate-500")}>
                Visualizes DOM updates and layout shifts in real-time. Useful for tracking down unnecessary re-renders in heavy components like tables and graphs.
            </p>

            <div className={cn("p-4 border rounded shrink-0", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-yellow-400" : "text-yellow-600")}>
                            <Zap className="w-4 h-4" /> Native Paint Flashing
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Highlights elements with colorful bounding boxes whenever they mutate or repaint via Render Profiler.</p>
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

            <div className={cn("p-4 border rounded shrink-0", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-green-400" : "text-green-600")}>
                            <Layers className="w-4 h-4" /> Component Render Flasher
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Highlights components with a green flash animation specifically when they re-render and mutate the DOM tree.</p>
                    </div>
                    <button
                        onClick={() => setReactFlashActive(!reactFlashActive)}
                        className={cn(
                            "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                            reactFlashActive
                                ? (isDark ? "bg-green-500/30 border-green-500 shadow-[0_0_15px_rgba(34,197,94,0.4)]" : "bg-green-100 border-green-500")
                                : (isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")
                        )}
                    >
                        <div
                            className={cn(
                                "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                                reactFlashActive
                                    ? (isDark ? "translate-x-6 bg-green-400 shadow-[0_0_10px_#22c55e]" : "translate-x-6 bg-green-500")
                                    : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                            )}
                        />
                    </button>
                </div>
            </div>
        </div>
    );
}
