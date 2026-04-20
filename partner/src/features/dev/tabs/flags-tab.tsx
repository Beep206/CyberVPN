import React from 'react';
import { Flag, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useFeatureFlags, FEATURE_FLAGS, FeatureFlagId } from '../lib/feature-flags';
import { motion } from 'motion/react';

export function FlagsTab({ isDark }: { isDark: boolean }) {
    const { flags, toggleFlag, resetFlags } = useFeatureFlags();

    return (
        <div className="space-y-4 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-purple to-neon-pink drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800")}>Feature Flags</h3>
                <button
                    onClick={resetFlags}
                    title="Reset to defaults"
                    className={cn(
                        "p-1.5 rounded transition-all flex items-center gap-1 text-xs font-bold",
                        isDark ? "hover:bg-gray-800 text-gray-400 hover:text-white" : "hover:bg-slate-200 text-slate-500 hover:text-slate-800"
                    )}
                >
                    <RotateCcw className="w-4 h-4" /> Reset
                </button>
            </div>

            <div className="space-y-3 overflow-y-auto pr-2 pb-4">
                {(Object.entries(FEATURE_FLAGS) as [FeatureFlagId, typeof FEATURE_FLAGS[FeatureFlagId]][]).map(([id, config]) => {
                    const isActive = flags[id];
                    return (
                        <div key={id} className={cn(
                            "flex items-center justify-between p-4 border rounded transition-colors",
                            isDark
                                ? "border-gray-800 bg-black/50 hover:border-gray-700"
                                : "border-slate-200 bg-white hover:border-blue-300"
                        )}>
                            <div className="flex gap-3 items-start">
                                <div className={cn("p-2 rounded mt-0.5", isDark ? "bg-gray-900" : "bg-slate-100")}>
                                    <Flag className={cn("w-4 h-4", isActive ? (isDark ? "text-neon-pink" : "text-blue-600") : "text-gray-500")} />
                                </div>
                                <div>
                                    <h4 className={cn("text-sm font-extrabold", isDark ? "text-gray-200" : "text-slate-800")}>{config.label}</h4>
                                    <p className={cn("text-xs mt-0.5 font-semibold", isDark ? "text-gray-500" : "text-slate-500")}>{config.description}</p>
                                    <code className={cn("text-[10px] px-1 py-0.5 rounded mt-1.5 inline-block", isDark ? "bg-gray-900 text-gray-400" : "bg-slate-100 text-slate-500")}>
                                        {id}
                                    </code>
                                </div>
                            </div>
                            <button
                                onClick={() => toggleFlag(id)}
                                className={cn(
                                    "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                                    isActive
                                        ? (isDark ? "bg-neon-pink/30 border-neon-pink shadow-[0_0_15px_rgba(255,0,255,0.4)]" : "bg-blue-100 border-blue-500")
                                        : (isDark ? "bg-gray-800 border-gray-600 shadow-[0_0_10px_rgba(0,0,0,0.5)]" : "bg-slate-200 border-slate-300")
                                )}
                            >
                                <motion.div
                                    className={cn(
                                        "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                                        isActive
                                            ? (isDark ? "translate-x-6 bg-neon-pink shadow-[0_0_10px_#ff00ff]" : "translate-x-6 bg-blue-500")
                                            : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                                    )}
                                    layout
                                />
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
