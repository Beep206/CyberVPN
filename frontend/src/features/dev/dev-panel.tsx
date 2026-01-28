"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, Shield, Navigation, Monitor, Settings, Globe } from "lucide-react";
import { DevButton } from "./dev-button";
import { cn } from "@/lib/utils";
import { usePathname, useRouter } from "next/navigation";

export function DevPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<"nav" | "auth" | "system" | "browser">("nav");
    const [bypassAuth, setBypassAuth] = useState(false);

    // Initial check for cookie on mount
    useEffect(() => {
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
                            className="pointer-events-auto relative w-full sm:w-[500px] h-[600px] bg-black border-2 border-neon-cyan text-neon-cyan overflow-hidden shadow-[0_0_100px_rgba(0,255,255,0.2)] rounded-lg clip-path-cyber"
                            style={{
                                clipPath: "polygon(0 0, 100% 0, 100% 90%, 95% 100%, 0 100%)"
                            }}
                        >
                            {/* CRT/Scanline Effect */}
                            <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px] z-10" />

                            {/* Header */}
                            <div className="relative z-20 flex items-center justify-between p-4 border-b border-neon-cyan/40 bg-black">
                                <div className="flex items-center gap-2">
                                    <Monitor className="h-5 w-5 text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,1)]" />
                                    <h2 className="font-display font-extrabold tracking-wider text-sm uppercase text-neon-cyan drop-shadow-[0_0_15px_rgba(0,255,255,0.9)]">
                                        Dev_Console <span className="text-neon-pink text-xs font-black animate-pulse drop-shadow-[0_0_15px_#ff00ff]">v1.0</span>
                                    </h2>
                                </div>
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-1 hover:bg-neon-pink/20 hover:text-neon-pink transition-colors rounded text-neon-cyan hover:shadow-[0_0_15px_#ff00ff]"
                                >
                                    <X className="h-5 w-5 font-bold" />
                                </button>
                            </div>

                            {/* Tab Navigation */}
                            <div className="relative z-20 flex border-b border-neon-cyan/40 bg-black">
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
                                                ? "text-neon-cyan bg-neon-cyan/10 drop-shadow-[0_0_10px_rgba(0,255,255,1)]"
                                                : "text-gray-400 hover:text-neon-pink hover:bg-neon-pink/10 hover:shadow-[inset_0_0_20px_rgba(255,0,255,0.2)]"
                                        )}
                                    >
                                        <tab.icon className={cn("h-4 w-4", activeTab === tab.id ? "drop-shadow-[0_0_10px_currentColor] text-neon-cyan" : "opacity-70")} />
                                        {tab.label}
                                        {activeTab === tab.id && (
                                            <motion.div
                                                layoutId="activeTab"
                                                className="absolute bottom-0 left-0 right-0 h-0.5 bg-neon-cyan shadow-[0_0_20px_#00ffff]"
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
                                        {activeTab === "nav" && <NavigationTab onClose={() => setIsOpen(false)} />}
                                        {activeTab === "auth" && <AuthTab enabled={bypassAuth} onToggle={toggleAuthBypass} />}
                                        {activeTab === "browser" && <BrowserTab />}
                                        {activeTab === "system" && <SystemTab />}
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

function NavigationTab({ onClose }: { onClose: () => void }) {
    const router = useRouter();
    const links = [
        { label: "Dashboard (User)", path: "/dashboard" },
        { label: "Login Page", path: "/login" },
        { label: "Landing Page", path: "/" },
    ];

    return (
        <div className="space-y-4 relative z-20">
            <h3 className="text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple font-extrabold text-sm uppercase tracking-widest mb-4 border-b border-neon-pink/50 pb-2 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]">Quick Jump</h3>
            <div className="grid gap-2">
                {links.map((link) => (
                    <button
                        key={link.path}
                        onClick={() => {
                            router.push(link.path);
                            onClose();
                        }}
                        className="group flex items-center justify-between p-3 border border-gray-700 bg-black hover:border-neon-cyan hover:bg-neon-cyan/20 transition-all rounded hover:shadow-[0_0_20px_rgba(0,255,255,0.4)] text-left"
                    >
                        <span className="text-base font-bold text-white group-hover:text-neon-cyan transition-colors group-hover:drop-shadow-[0_0_8px_rgba(0,255,255,1)]">{link.label}</span>
                        <span className="text-xs text-gray-400 font-mono group-hover:text-neon-pink transition-colors font-medium">{link.path}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}

function AuthTab({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
    return (
        <div className="space-y-4 relative z-20">
            <h3 className="text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple font-extrabold text-sm uppercase tracking-widest mb-4 border-b border-neon-pink/50 pb-2 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]">Security Protocols</h3>

            <div className="flex items-center justify-between p-4 border border-neon-cyan/40 bg-black rounded backdrop-blur-md hover:border-neon-cyan/60 transition-colors">
                <div>
                    <h4 className="text-base font-extrabold text-neon-cyan drop-shadow-[0_0_10px_rgba(0,255,255,0.9)]">Auth Bypass Mode</h4>
                    <p className="text-xs text-gray-300 mt-1 font-semibold group-hover:text-white transition-colors">Simulate authenticated session via cookie injection.</p>
                </div>
                <button
                    onClick={onToggle}
                    className={cn(
                        "relative w-14 h-7 rounded-full transition-colors duration-300 focus:outline-none border-2 shadow-[0_0_15px_rgba(0,0,0,0.5)]",
                        enabled ? "bg-neon-cyan/30 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.5)]" : "bg-gray-800 border-gray-500 hover:border-neon-pink/50"
                    )}
                >
                    <motion.div
                        className={cn(
                            "absolute top-0.5 left-0.5 w-5 h-5 rounded-full shadow-md transition-transform duration-300",
                            enabled ? "translate-x-7 bg-neon-cyan shadow-[0_0_15px_#00ffff]" : "translate-x-0 bg-gray-400"
                        )}
                        layout
                    />
                </button>
            </div>

            <div className="p-3 bg-yellow-900/40 border border-yellow-500/50 rounded text-xs text-yellow-300 font-mono font-bold shadow-[0_0_15px_rgba(234,179,8,0.2)]">
                <p>⚠ Enabling bypass sets <code className="text-white bg-black/50 px-1 rounded">DEV_BYPASS_AUTH</code> cookie. Middleware will permit access.</p>
            </div>
        </div>
    );
}

function SystemTab() {
    return (
        <div className="space-y-4 relative z-20">
            <h3 className="text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple font-extrabold text-sm uppercase tracking-widest mb-4 border-b border-neon-pink/50 pb-2 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]">System Diagnostics</h3>

            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 bg-black border border-gray-700 rounded hover:border-neon-cyan/50 transition-colors group">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">NODE_ENV</span>
                    <span className="text-white font-black text-sm tracking-wide drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]">{process.env.NODE_ENV}</span>
                </div>
                <div className="p-3 bg-black border border-gray-700 rounded hover:border-neon-cyan/50 transition-colors group">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">Platform</span>
                    <span className="text-white font-black text-sm tracking-wide drop-shadow-[0_0_5px_rgba(255,255,255,0.7)]">{typeof window !== 'undefined' ? window.navigator.platform : 'Server'}</span>
                </div>
                <div className="p-3 bg-black border border-gray-700 rounded col-span-2 hover:border-neon-cyan/50 transition-colors group">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">User Agent</span>
                    <span className="text-gray-100 break-all font-semibold group-hover:text-neon-cyan transition-colors">{typeof window !== 'undefined' ? window.navigator.userAgent : 'Server'}</span>
                </div>
            </div>
        </div>
    );
}

function BrowserTab() {
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
                // @ts-ignore
                memory: navigator.deviceMemory || 0,
            });

            const interval = setInterval(() => {
                setInfo(prev => ({ ...prev, time: new Date().toLocaleTimeString() }));
            }, 1000);

            return () => clearInterval(interval);
        }
    }, []);

    return (
        <div className="space-y-4 relative z-20">
            <h3 className="text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple font-extrabold text-sm uppercase tracking-widest mb-4 border-b border-neon-pink/50 pb-2 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]">Browser Intelligence</h3>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 bg-black border border-gray-800 rounded group hover:border-neon-cyan/50 transition-all">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">Language</span>
                    <span className="text-white font-bold">{info.language}</span>
                </div>
                <div className="p-3 bg-black border border-gray-800 rounded group hover:border-neon-cyan/50 transition-all">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">Local Time</span>
                    <span className="text-neon-cyan font-bold animate-pulse">{info.time}</span>
                </div>
                <div className="p-3 bg-black border border-gray-800 rounded group hover:border-neon-cyan/50 transition-all">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">Resolution</span>
                    <span className="text-white font-bold">{info.screen}</span>
                </div>
                <div className="p-3 bg-black border border-gray-800 rounded group hover:border-neon-cyan/50 transition-all">
                    <span className="block text-neon-pink font-bold mb-1 drop-shadow-[0_0_5px_rgba(255,0,255,0.5)]">CPU Cores</span>
                    <span className="text-white font-bold">{info.cores}</span>
                </div>
            </div>

            <div className="relative mt-4 p-4 border border-neon-cyan/30 bg-black/80 rounded overflow-hidden group">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-50" />
                <h4 className="text-neon-cyan font-bold text-xs mb-2 drop-shadow-[0_0_5px_rgba(0,255,255,0.8)]">Environment Scan</h4>
                <div className="space-y-1">
                    <div className="flex justify-between text-[10px]">
                        <span className="text-gray-400">Cookies</span>
                        <span className="text-green-400 font-bold">{typeof window !== 'undefined' && navigator.cookieEnabled ? "ENABLED" : "DISABLED"}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                        <span className="text-gray-400">Online Status</span>
                        <span className="text-green-400 font-bold">{typeof window !== 'undefined' && navigator.onLine ? "ONLINE" : "OFFLINE"}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
