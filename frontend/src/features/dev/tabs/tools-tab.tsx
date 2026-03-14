import { useState, useEffect } from "react";
import { Layout, Trash2, Server } from "lucide-react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export function ToolsTab({ isDark }: { isDark: boolean }) {
    const [outlines, setOutlines] = useState(false);
    const [rscActive, setRscActive] = useState(false);

    /* eslint-disable react-hooks/set-state-in-effect -- Restore dev outlines on mount */
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('DEV_OUTLINES');
            if (saved === 'true') {
                setOutlines(true);
            }
        }
    }, []);
    /* eslint-enable react-hooks/set-state-in-effect */

    // Sync to localStorage and inject styles
    useEffect(() => {
        if (typeof window === 'undefined') return;
        
        const styleId = 'dev-outlines-style';
        let style = document.getElementById(styleId);

        if (outlines) {
            localStorage.setItem('DEV_OUTLINES', 'true');
            if (!style) {
                style = document.createElement('style');
                style.id = styleId;
                document.head.appendChild(style);
            }
            style.innerHTML = `* { outline: 1px solid ${isDark ? 'rgba(0, 255, 255, 0.4)' : 'rgba(0, 0, 255, 0.4)'} !important; }`;
        } else {
            localStorage.removeItem('DEV_OUTLINES');
            style?.remove();
        }
    }, [outlines, isDark]);

    // RSC vs Client Highlighter
    useEffect(() => {
        if (typeof window === 'undefined') return;

        const styleId = 'dev-rsc-style';
        if (rscActive) {
            const style = document.createElement('style');
            style.id = styleId;
            style.innerHTML = `
                body *:not(#dev-panel-root):not(#dev-panel-root *) {
                    outline: 2px solid rgba(59, 130, 246, 0.4) !important; /* Server (Blue) */
                    outline-offset: -2px;
                }
                body button, body input, body select, body textarea, body a, body [role="button"], body [tabindex] {
                    outline: 2px solid rgba(234, 179, 8, 0.7) !important; /* Client (Yellow) */
                    outline-offset: -2px;
                    background-color: rgba(234, 179, 8, 0.1) !important;
                }
            `;
            document.head.appendChild(style);
        } else {
            document.getElementById(styleId)?.remove();
        }

        return () => {
            document.getElementById(styleId)?.remove();
        };
    }, [rscActive]);

    const handleClearStorage = (type: 'local' | 'session' | 'cookies') => {
        if (typeof window !== 'undefined') {
            if (type === 'local') localStorage.clear();
            if (type === 'session') sessionStorage.clear();
            if (type === 'cookies') {
                document.cookie.split(";").forEach((c) => {
                    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
                });
            }
            alert(`${type.toUpperCase()} Storage & Cookies cleared successfully.`);
        }
    };

    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Developer Tools</h3>

            {/* Layout Debugger */}
            <div className={cn(
                "flex items-center justify-between p-4 border rounded transition-colors",
                isDark
                    ? "border-neon-cyan/40 bg-black hover:border-neon-cyan/60"
                    : "border-slate-200 bg-white hover:border-blue-300"
            )}>
                <div className="flex gap-3 items-center">
                    <div className={cn("p-2 rounded", isDark ? "bg-neon-cyan/10" : "bg-blue-50")}>
                        <Layout className={cn("w-5 h-5", isDark ? "text-neon-cyan" : "text-blue-500")} />
                    </div>
                    <div>
                        <h4 className={cn("text-base font-extrabold", isDark ? "text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,0.9)]" : "text-slate-800")}>CSS Layout Debugger</h4>
                        <p className={cn("text-xs mt-1 font-semibold transition-colors", isDark ? "text-gray-300" : "text-slate-500")}>Highlights all DOM elements with outlines.</p>
                    </div>
                </div>
                <button
                    onClick={() => setOutlines(!outlines)}
                    className={cn(
                        "relative w-14 h-7 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                        outlines
                            ? (isDark ? "bg-neon-cyan/30 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.5)]" : "bg-blue-100 border-blue-500")
                            : (isDark ? "bg-gray-800 border-gray-500 shadow-[0_0_15px_rgba(0,0,0,0.5)]" : "bg-slate-200 border-slate-300")
                    )}
                >
                    <motion.div
                        className={cn(
                            "absolute top-0.5 left-0.5 w-5 h-5 rounded-full shadow-md transition-transform duration-300",
                            outlines
                                ? (isDark ? "translate-x-7 bg-neon-cyan shadow-[0_0_15px_#00ffff]" : "translate-x-7 bg-blue-500")
                                : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                        )}
                        layout
                    />
                </button>
            </div>

            {/* RSC vs Client Highlighter */}
            <div className={cn(
                "flex items-center justify-between p-4 border rounded transition-colors",
                isDark
                    ? "border-purple-900/40 bg-black hover:border-purple-500/60"
                    : "border-slate-200 bg-white hover:border-purple-300"
            )}>
                <div className="flex gap-3 items-center">
                    <div className={cn("p-2 rounded", isDark ? "bg-purple-500/10" : "bg-purple-50")}>
                        <Server className={cn("w-5 h-5", isDark ? "text-purple-400" : "text-purple-500")} />
                    </div>
                    <div>
                        <h4 className={cn("text-base font-extrabold", isDark ? "text-purple-400 drop-shadow-[0_0_10px_rgba(168,85,247,0.5)]" : "text-purple-700")}>RSC vs Client Highlight</h4>
                        <p className={cn("text-xs mt-1 font-semibold transition-colors", isDark ? "text-gray-400" : "text-slate-500")}>Highlights Server Components (Blue) and Client Islands (Yellow).</p>
                    </div>
                </div>
                <button
                    onClick={() => setRscActive(!rscActive)}
                    className={cn(
                        "relative w-14 h-7 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                        rscActive
                            ? (isDark ? "bg-purple-500/30 border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.5)]" : "bg-purple-100 border-purple-500")
                            : (isDark ? "bg-gray-800 border-gray-500 shadow-[0_0_15px_rgba(0,0,0,0.5)]" : "bg-slate-200 border-slate-300")
                    )}
                >
                    <motion.div
                        className={cn(
                            "absolute top-0.5 left-0.5 w-5 h-5 rounded-full shadow-md transition-transform duration-300",
                            rscActive
                                ? (isDark ? "translate-x-7 bg-purple-400 shadow-[0_0_15px_#a855f7]" : "translate-x-7 bg-purple-500")
                                : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                        )}
                        layout
                    />
                </button>
            </div>

            {/* Storage Wipe */}
            <div className={cn(
                "p-4 border rounded transition-colors space-y-3",
                isDark ? "border-red-900/50 bg-black hover:border-red-500/50" : "border-red-200 bg-red-50/30 hover:border-red-300"
            )}>
                <div className="flex gap-3 items-center mb-2">
                    <div className={cn("p-2 rounded", isDark ? "bg-red-500/10" : "bg-red-100")}>
                        <Trash2 className={cn("w-5 h-5", isDark ? "text-red-400" : "text-red-500")} />
                    </div>
                    <div>
                        <h4 className={cn("text-base font-extrabold", isDark ? "text-red-400 drop-shadow-[0_0_10px_rgba(255,0,0,0.5)]" : "text-red-700")}>State Management Nuke</h4>
                        <p className={cn("text-xs mt-1 font-semibold", isDark ? "text-gray-400" : "text-slate-500")}>Clear client-side storage to re-test scenarios.</p>
                    </div>
                </div>
                
                <div className="grid grid-cols-3 gap-2">
                    <button
                        onClick={() => handleClearStorage('local')}
                        className={cn(
                            "py-2 px-2 rounded text-[10px] md:text-xs font-bold transition-all border text-center",
                            isDark 
                                ? "bg-black border-red-900 text-red-400 hover:bg-red-950 hover:border-red-500" 
                                : "bg-white border-red-200 text-red-600 hover:bg-red-50"
                        )}
                    >
                        Local
                    </button>
                    <button
                        onClick={() => handleClearStorage('session')}
                        className={cn(
                            "py-2 px-2 rounded text-[10px] md:text-xs font-bold transition-all border text-center",
                            isDark 
                                ? "bg-black border-orange-900 text-orange-400 hover:bg-orange-950 hover:border-orange-500" 
                                : "bg-white border-orange-200 text-orange-600 hover:bg-orange-50"
                        )}
                    >
                        Session
                    </button>
                    <button
                        onClick={() => handleClearStorage('cookies')}
                        className={cn(
                            "py-2 px-2 rounded text-[10px] md:text-xs font-bold transition-all border text-center",
                            isDark 
                                ? "bg-black border-yellow-900 text-yellow-400 hover:bg-yellow-950 hover:border-yellow-500" 
                                : "bg-white border-yellow-200 text-yellow-600 hover:bg-yellow-50"
                        )}
                    >
                        Cookies
                    </button>
                </div>
            </div>
        </div>
    );
}
