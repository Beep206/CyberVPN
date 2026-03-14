import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export function AuthTab({ enabled, onToggle, isDark }: { enabled: boolean; onToggle: () => void, isDark: boolean }) {
    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Security Protocols</h3>

            <div className={cn(
                "flex items-center justify-between p-4 border rounded backdrop-blur-md transition-colors",
                isDark
                    ? "border-neon-cyan/40 bg-black hover:border-neon-cyan/60"
                    : "border-slate-200 bg-white hover:border-blue-300"
            )}>
                <div>
                    <h4 className={cn("text-base font-extrabold", isDark ? "text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,0.9)]" : "text-slate-800")}>Auth Bypass Mode</h4>
                    <p className={cn("text-xs mt-1 font-semibold transition-colors", isDark ? "text-gray-300 group-hover:text-white" : "text-slate-500")}>Simulate authenticated session via cookie injection.</p>
                </div>
                <button
                    onClick={onToggle}
                    className={cn(
                        "relative w-14 h-7 rounded-full transition-colors duration-300 focus:outline-none border-2",
                        enabled
                            ? (isDark ? "bg-neon-cyan/30 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.5)]" : "bg-blue-100 border-blue-500")
                            : (isDark ? "bg-gray-800 border-gray-500 hover:border-neon-pink/50 shadow-[0_0_15px_rgba(0,0,0,0.5)]" : "bg-slate-200 border-slate-300")
                    )}
                >
                    <motion.div
                        className={cn(
                            "absolute top-0.5 left-0.5 w-5 h-5 rounded-full shadow-md transition-transform duration-300",
                            enabled
                                ? (isDark ? "translate-x-7 bg-neon-cyan shadow-[0_0_15px_#00ffff]" : "translate-x-7 bg-blue-500")
                                : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                        )}
                        layout
                    />
                </button>
            </div>

            <div className={cn(
                "p-3 rounded text-xs font-mono font-bold border",
                isDark
                    ? "bg-yellow-900/40 border-yellow-500/50 text-yellow-300 shadow-[0_0_15px_rgba(234,179,8,0.2)]"
                    : "bg-amber-50 border-amber-200 text-amber-700"
            )}>
                <p>⚠ Enabling bypass sets <code className={cn("px-1 rounded", isDark ? "text-white bg-black/50" : "bg-white border border-amber-200")}>DEV_BYPASS_AUTH</code> cookie. Middleware will permit access.</p>
            </div>
        </div>
    );
}
