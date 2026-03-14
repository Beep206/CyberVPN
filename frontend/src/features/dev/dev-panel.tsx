"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, Shield, Navigation, Monitor, Settings, Globe, Wrench, Activity, Flag, Skull, Languages, Palette } from "lucide-react";
import { DevButton } from "./dev-button";
import { cn } from "@/lib/utils";
import { useTheme } from "next-themes";

import { NavigationTab } from "./tabs/navigation-tab";
import { AuthTab } from "./tabs/auth-tab";
import { BrowserTab } from "./tabs/browser-tab";
import { SystemTab } from "./tabs/system-tab";
import { PerformanceTab } from "./tabs/performance-tab";
import { ToolsTab } from "./tabs/tools-tab";
import { NetworkTab } from "./tabs/network-tab";
import { FlagsTab } from "./tabs/flags-tab";
import { ChaosTab } from "./tabs/chaos-tab";
import { I18nTab } from "./tabs/i18n-tab";
import { ThemeTab } from "./tabs/theme-tab";
import { networkLogger } from "./lib/network-logger";

export function DevPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<"nav" | "auth" | "system" | "browser" | "performance" | "network" | "flags" | "chaos" | "i18n" | "theme" | "tools">("nav");
    const [bypassAuth, setBypassAuth] = useState(false);
    const { resolvedTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    /* eslint-disable react-hooks/set-state-in-effect -- Dev-only hydration guard and cookie check on mount */
    useEffect(() => {
        setMounted(true);
        setBypassAuth(document.cookie.split(';').some((item) => item.trim().startsWith('DEV_BYPASS_AUTH=')));

        // Global Persistence Initializations for Dev Panel features
        networkLogger.start();

        if (typeof window !== 'undefined') {
            // Restore RTL setting
            if (localStorage.getItem('DEV_RTL') === 'true') {
                document.documentElement.dir = 'rtl';
            }

            // Restore Custom Theme
            const savedTheme = localStorage.getItem('DEV_THEME');
            if (savedTheme) {
                try {
                    const parsedTheme = JSON.parse(savedTheme);
                    Object.entries(parsedTheme).forEach(([key, val]) => {
                        document.documentElement.style.setProperty(key, val as string);
                    });
                } catch { /* ignore */ }
            }
        }
    }, []);
    /* eslint-enable react-hooks/set-state-in-effect */

    const toggleAuthBypass = () => {
        if (bypassAuth) {
            document.cookie = "DEV_BYPASS_AUTH=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            setBypassAuth(false);
        } else {
            document.cookie = "DEV_BYPASS_AUTH=true; path=/; max-age=31536000"; // 1 year
            setBypassAuth(true);
        }
    };

    if (!mounted) return <DevButton onClick={() => setIsOpen(true)} />;

    const isDark = resolvedTheme === 'dark';

    return (
        <>
            <DevButton onClick={() => setIsOpen(true)} />

            <AnimatePresence>
                {isOpen && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">
                        {/* Backdrop */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsOpen(false)}
                            className="absolute inset-0 bg-black/60 backdrop-blur-md pointer-events-auto"
                        />

                        {/* Modal */}
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            transition={{ type: "spring", bounce: 0.3, duration: 0.5 }}
                            className={cn(
                                "pointer-events-auto relative w-full sm:w-[600px] h-[600px] overflow-hidden rounded-lg clip-path-cyber transition-colors duration-300",
                                isDark
                                    ? "bg-black border-2 border-neon-cyan text-neon-cyan shadow-[0_0_100px_rgba(0,255,255,0.2)]"
                                    : "bg-white border-2 border-slate-200 text-slate-800 shadow-2xl"
                            )}
                            style={{
                                clipPath: "polygon(0 0, 100% 0, 100% 90%, 95% 100%, 0 100%)"
                            }}
                        >
                            {/* CRT/Scanline Effect (Dark Only) */}
                            {isDark && (
                                <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px] z-10" />
                            )}

                            {/* Header */}
                            <div className={cn(
                                "relative z-20 flex items-center justify-between p-4 border-b transition-colors",
                                isDark ? "border-neon-cyan/40 bg-black" : "border-slate-200 bg-slate-50"
                            )}>
                                <div className="flex items-center gap-2">
                                    <Monitor className={cn("h-5 w-5", isDark ? "text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,1)]" : "text-slate-600")} />
                                    <h2 className={cn(
                                        "font-display font-extrabold tracking-wider text-sm uppercase",
                                        isDark ? "text-neon-cyan drop-shadow-[0_0_15px_rgba(0,255,255,0.9)]" : "text-slate-800"
                                    )}>
                                        Dev_Console <span className={cn("text-xs font-black", isDark ? "text-neon-pink animate-pulse drop-shadow-[0_0_15px_#ff00ff]" : "text-blue-500")}>v2.0</span>
                                    </h2>
                                </div>
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className={cn(
                                        "p-1 rounded transition-colors transition-all",
                                        isDark
                                            ? "hover:bg-neon-pink/20 hover:text-neon-pink text-neon-cyan hover:shadow-[0_0_15px_#ff00ff]"
                                            : "hover:bg-red-100 hover:text-red-500 text-slate-400"
                                    )}
                                >
                                    <X className="h-5 w-5 font-bold" />
                                </button>
                            </div>

                            {/* Tab Navigation */}
                            <div className={cn(
                                "relative z-20 flex border-b transition-colors overflow-x-auto",
                                isDark ? "border-neon-cyan/40 bg-black" : "border-slate-200 bg-white"
                            )}>
                                {([
                                    { id: "nav", icon: Navigation, label: "Nav" },
                                    { id: "auth", icon: Shield, label: "Auth" },
                                    { id: "browser", icon: Globe, label: "Browser" },
                                    { id: "system", icon: Settings, label: "System" },
                                    { id: "performance", icon: Monitor, label: "Perf" },
                                    { id: "network", icon: Activity, label: "Net" },
                                    { id: "flags", icon: Flag, label: "Flags" },
                                    { id: "chaos", icon: Skull, label: "Chaos" },
                                    { id: "i18n", icon: Languages, label: "i18n" },
                                    { id: "theme", icon: Palette, label: "Theme" },
                                    { id: "tools", icon: Wrench, label: "Tools" },
                                ] as const).map((tab) => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={cn(
                                            "flex-1 min-w-fit px-4 flex items-center justify-center gap-2 py-3 text-sm font-black font-mono uppercase tracking-tight transition-all relative overflow-hidden",
                                            activeTab === tab.id
                                                ? (isDark ? "text-neon-cyan bg-neon-cyan/10 drop-shadow-[0_0_10px_rgba(0,255,255,1)]" : "text-blue-600 bg-blue-50")
                                                : (isDark ? "text-gray-400 hover:text-neon-pink hover:bg-neon-pink/10 hover:shadow-[inset_0_0_20px_rgba(255,0,255,0.2)]" : "text-slate-400 hover:text-slate-600 hover:bg-slate-50")
                                        )}
                                    >
                                        <tab.icon className={cn("h-4 w-4 shrink-0",
                                            activeTab === tab.id
                                                ? (isDark ? "drop-shadow-[0_0_10px_currentColor] text-neon-cyan" : "text-blue-600")
                                                : "opacity-70"
                                        )} />
                                        {tab.label}
                                        {activeTab === tab.id && (
                                            <motion.div
                                                layoutId="activeTab"
                                                className={cn("absolute bottom-0 left-0 right-0 h-0.5", isDark ? "bg-neon-cyan shadow-[0_0_20px_#00ffff]" : "bg-blue-600")}
                                            />
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Content Area */}
                            <div className="relative z-20 p-6 overflow-y-auto h-[calc(100%-110px)] font-mono space-y-6">
                                <AnimatePresence mode="wait">
                                    <motion.div
                                        key={activeTab}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                        transition={{ duration: 0.2 }}
                                    >
                                        {activeTab === "nav" && <NavigationTab onClose={() => setIsOpen(false)} isDark={isDark} />}
                                        {activeTab === "auth" && <AuthTab enabled={bypassAuth} onToggle={toggleAuthBypass} isDark={isDark} />}
                                        {activeTab === "browser" && <BrowserTab isDark={isDark} />}
                                        {activeTab === "system" && <SystemTab isDark={isDark} />}
                                        {activeTab === "performance" && <PerformanceTab isDark={isDark} />}
                                        {activeTab === "network" && <NetworkTab isDark={isDark} />}
                                        {activeTab === "flags" && <FlagsTab isDark={isDark} />}
                                        {activeTab === "chaos" && <ChaosTab isDark={isDark} />}
                                        {activeTab === "i18n" && <I18nTab isDark={isDark} />}
                                        {activeTab === "theme" && <ThemeTab isDark={isDark} />}
                                        {activeTab === "tools" && <ToolsTab isDark={isDark} />}
                                    </motion.div>
                                </AnimatePresence>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}
