import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

export function BrowserTab({ isDark }: { isDark: boolean }) {
    const [info, setInfo] = useState({
        language: "",
        time: "",
        screen: "",
        viewport: "",
        breakpoint: "",
        cores: 0,
        memory: 0,
    });

    const getBreakpoint = (width: number) => {
        if (width < 640) return "xs";
        if (width < 768) return "sm";
        if (width < 1024) return "md";
        if (width < 1280) return "lg";
        if (width < 1536) return "xl";
        return "2xl";
    };

    /* eslint-disable react-hooks/set-state-in-effect -- Dev-only browser info collection on mount */
    useEffect(() => {
        if (typeof window !== "undefined") {
            const updateInfo = () => {
                setInfo(prev => ({
                    ...prev,
                    screen: `${window.screen.width}x${window.screen.height}`,
                    viewport: `${window.innerWidth}x${window.innerHeight}`,
                    breakpoint: getBreakpoint(window.innerWidth),
                    time: new Date().toLocaleTimeString()
                }));
            };

            setInfo({
                language: navigator.language,
                time: new Date().toLocaleTimeString(),
                screen: `${window.screen.width}x${window.screen.height}`,
                viewport: `${window.innerWidth}x${window.innerHeight}`,
                breakpoint: getBreakpoint(window.innerWidth),
                cores: navigator.hardwareConcurrency || 0,
                memory: (navigator as unknown as { deviceMemory?: number }).deviceMemory ?? 0,
            });

            window.addEventListener('resize', updateInfo);
            const interval = setInterval(() => {
                setInfo(prev => ({ ...prev, time: new Date().toLocaleTimeString() }));
            }, 1000);

            return () => {
                clearInterval(interval);
                window.removeEventListener('resize', updateInfo);
            };
        }
    }, []);
    /* eslint-enable react-hooks/set-state-in-effect */

    return (
        <div className="space-y-4 relative z-20">
            <h3 className={cn("font-extrabold text-sm uppercase tracking-widest mb-4 border-b pb-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-pink to-neon-purple border-neon-pink/50 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-slate-800 border-slate-200")}>Browser Intelligence</h3>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                {[
                    { label: "Language", value: info.language },
                    { label: "Local Time", value: info.time, highlight: true },
                    { label: "Screen Res", value: info.screen },
                    { label: "Viewport", value: `${info.viewport} (${info.breakpoint})` },
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
