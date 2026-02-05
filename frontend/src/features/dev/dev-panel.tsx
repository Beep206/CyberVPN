"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, Shield, Navigation, Monitor, Settings, Globe } from "lucide-react";
import { DevButton } from "./dev-button";
import { cn } from "@/lib/utils";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";

export function DevPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<"nav" | "auth" | "system" | "browser">("nav");
    const [bypassAuth, setBypassAuth] = useState(false);
    const { resolvedTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        // Initial check for cookie on mount
        const hasCookie = document.cookie.split(';').some((item) => item.trim().startsWith('DEV_BYPASS_AUTH='));
        setBypassAuth(hasCookie);
    }, []);

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
                                "pointer-events-auto relative w-full sm:w-[500px] h-[600px] overflow-hidden rounded-lg clip-path-cyber transition-colors duration-300",
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
                                "relative z-20 flex border-b transition-colors",
                                isDark ? "border-neon-cyan/40 bg-black" : "border-slate-200 bg-white"
                            )}>
                                {([
                                    { id: "nav", icon: Navigation, label: "Navigation" },
                                    { id: "auth", icon: Shield, label: "Auth" },
                                    { id: "browser", icon: Globe, label: "Browser" },
                                    { id: "system", icon: Settings, label: "System" },
                                ] as const).map((tab) => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={cn(
                                            "flex-1 flex items-center justify-center gap-2 py-3 text-sm font-black font-mono uppercase tracking-tight transition-all relative overflow-hidden",
                                            activeTab === tab.id
                                                ? (isDark ? "text-neon-cyan bg-neon-cyan/10 drop-shadow-[0_0_10px_rgba(0,255,255,1)]" : "text-blue-600 bg-blue-50")
                                                : (isDark ? "text-gray-400 hover:text-neon-pink hover:bg-neon-pink/10 hover:shadow-[inset_0_0_20px_rgba(255,0,255,0.2)]" : "text-slate-400 hover:text-slate-600 hover:bg-slate-50")
                                        )}
                                    >
                                        <tab.icon className={cn("h-4 w-4",
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

// --- Subcomponents for Tabs ---

function NavigationTab({ onClose, isDark }: { onClose: () => void, isDark: boolean }) {
    const router = useRouter();
    const links = [
        { label: "Dashboard (User)", path: "/dashboard" },
        { label: "Login Page", path: "/login" },
        { label: "Landing Page", path: "/" },
        { label: "Registration Page", path: "/register" },
        { label: "OTP Verification", path: "/verify" },
        { label: "Inception Test", path: "/test-animation" },
    ];

    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Quick Jump</h3>
            <div className="grid gap-2">
                {links.map((link) => (
                    <button
                        key={link.path}
                        onClick={() => {
                            router.push(link.path);
                            onClose();
                        }}
                        className={cn(
                            "group flex items-center justify-between p-3 border transition-all rounded text-left",
                            isDark
                                ? "border-gray-700 bg-black hover:border-neon-cyan hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,255,255,0.4)]"
                                : "border-slate-200 bg-white hover:border-blue-400 hover:bg-blue-50 shadow-sm"
                        )}
                    >
                        <span className={cn("text-base font-bold transition-colors", isDark ? "text-white group-hover:text-neon-cyan group-hover:drop-shadow-[0_0_8px_rgba(0,255,255,1)]" : "text-slate-700 group-hover:text-blue-600")}>{link.label}</span>
                        <span className={cn("text-xs font-mono transition-colors font-medium", isDark ? "text-gray-400 group-hover:text-neon-pink" : "text-slate-400 group-hover:text-blue-400")}>{link.path}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}

function AuthTab({ enabled, onToggle, isDark }: { enabled: boolean; onToggle: () => void, isDark: boolean }) {
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

function SystemTab({ isDark }: { isDark: boolean }) {
    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>System Diagnostics</h3>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className={cn("p-3 border rounded transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>NODE_ENV</span>
                    <span className={cn("font-black text-sm tracking-wide", isDark ? "text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]" : "text-slate-800")}>{process.env.NODE_ENV}</span>
                </div>
                <div className={cn("p-3 border rounded transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>Platform</span>
                    <span className={cn("font-black text-sm tracking-wide", isDark ? "text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]" : "text-slate-800")}>{typeof window !== 'undefined' ? window.navigator.platform : 'Server'}</span>
                </div>
                <div className={cn("p-3 border rounded col-span-2 transition-colors group", isDark ? "bg-black border-gray-700 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                    <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>User Agent</span>
                    <span className={cn("break-all font-semibold transition-colors", isDark ? "text-gray-100 group-hover:text-neon-cyan" : "text-slate-700")}>{typeof window !== 'undefined' ? window.navigator.userAgent : 'Server'}</span>
                </div>
            </div>
        </div>
    );
}

function BrowserTab({ isDark }: { isDark: boolean }) {
    const [info, setInfo] = useState({
        language: "",
        time: "",
        screen: "",
        cores: 0,
        memory: 0,
    });

    useEffect(() => {
        if (typeof window !== "undefined") {
            setInfo({
                language: navigator.language,
                time: new Date().toLocaleTimeString(),
                screen: `${window.screen.width}x${window.screen.height}`,
                cores: navigator.hardwareConcurrency || 0,
                memory: (navigator as unknown as { deviceMemory?: number }).deviceMemory ?? 0,
            });

            const interval = setInterval(() => {
                setInfo(prev => ({ ...prev, time: new Date().toLocaleTimeString() }));
            }, 1000);

            return () => clearInterval(interval);
        }
    }, []);

    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Browser Intelligence</h3>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                {[
                    { label: "Language", value: info.language },
                    { label: "Local Time", value: info.time, highlight: true },
                    { label: "Resolution", value: info.screen },
                    { label: "CPU Cores", value: info.cores },
                ].map((item) => (
                    <div key={item.label} className={cn("p-3 border rounded group transition-all", isDark ? "bg-black border-gray-800 hover:border-neon-cyan/50" : "bg-white border-slate-200 shadow-sm")}>
                        <span className={cn("block font-bold mb-1", isDark ? "text-neon-pink drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]" : "text-slate-500")}>{item.label}</span>
                        <span className={cn("font-bold", item.highlight && isDark ? "text-neon-cyan animate-pulse" : (isDark ? "text-white" : "text-slate-800"))}>{item.value}</span>
                    </div>
                ))}
            </div>

            <div className={cn(
                "relative mt-4 p-4 border rounded overflow-hidden group",
                isDark ? "border-neon-cyan/30 bg-black/80" : "border-blue-200 bg-blue-50/50"
            )}>
                <div className={cn("absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent to-transparent opacity-50", isDark ? "via-neon-cyan" : "via-blue-400")} />
                <h4 className={cn("font-bold text-xs mb-2", isDark ? "text-neon-cyan drop-shadow-[0_0_5px_rgba(0,255,255,0.8)]" : "text-blue-700")}>Environment Scan</h4>
                <div className="space-y-1">
                    <div className="flex justify-between text-[10px]">
                        <span className={isDark ? "text-gray-400" : "text-slate-500"}>Cookies</span>
                        <span className={cn("font-bold", isDark ? "text-green-400" : "text-green-600")}>{typeof window !== 'undefined' && navigator.cookieEnabled ? "ENABLED" : "DISABLED"}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                        <span className={isDark ? "text-gray-400" : "text-slate-500"}>Online Status</span>
                        <span className={cn("font-bold", isDark ? "text-green-400" : "text-green-600")}>{typeof window !== 'undefined' && navigator.onLine ? "ONLINE" : "OFFLINE"}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
