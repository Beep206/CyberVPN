import React, { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { Wifi, WifiOff, MapPin, Gauge, Globe2 } from "lucide-react";

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

    // Geo Mocking State
    const [geoMock, setGeoMock] = useState<"real" | "ny" | "tokyo" | "london" | "null">("real");

    // Net Throttling State
    const [netThrottle, setNetThrottle] = useState<"none" | "fast3g" | "slow3g" | "offline">("none");

    const originalFetch = useRef<typeof window.fetch | null>(null);
    const originalGeo = useRef<Geolocation | null>(null);

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

    // Network Throttling Interceptor
    useEffect(() => {
        if (typeof window === 'undefined') return;

        if (!originalFetch.current) {
            originalFetch.current = window.fetch;
        }

        const restoreFetch = () => {
            if (originalFetch.current) window.fetch = originalFetch.current;
        };

        if (netThrottle === "none") {
            restoreFetch();
            return;
        }

        const delay = netThrottle === "fast3g" ? 500 : netThrottle === "slow3g" ? 2000 : 0;

        window.fetch = async (...args) => {
            if (netThrottle === "offline") {
                throw new TypeError("Failed to fetch");
            }
            if (delay > 0) {
                await new Promise(r => setTimeout(r, delay));
            }
            return originalFetch.current!(...args);
        };

        return restoreFetch;
    }, [netThrottle]);

    // Geolocation Mocking Interceptor
    useEffect(() => {
        if (typeof window === 'undefined') return;
        if (!navigator.geolocation) return;

        if (!originalGeo.current) {
            originalGeo.current = navigator.geolocation;
        }

        const restoreGeo = () => {
            if (originalGeo.current) {
                Object.defineProperty(navigator, 'geolocation', { value: originalGeo.current, configurable: true });
            }
        };

        if (geoMock === "real") {
            restoreGeo();
            return;
        }

        const coordsMap = {
            ny: { latitude: 40.7128, longitude: -74.0060 },
            tokyo: { latitude: 35.6762, longitude: 139.6503 },
            london: { latitude: 51.5074, longitude: -0.1278 },
            null: { latitude: 0, longitude: 0 }
        };

        const mockCords = coordsMap[geoMock as keyof typeof coordsMap];

        const mockGeolocation = {
            getCurrentPosition: (success: PositionCallback, error?: PositionErrorCallback, options?: PositionOptions) => {
                success({
                    coords: {
                        latitude: mockCords.latitude,
                        longitude: mockCords.longitude,
                        accuracy: 10, altitude: null, altitudeAccuracy: null, heading: null, speed: null,
                    } as unknown as GeolocationCoordinates,
                    timestamp: Date.now()
                } as unknown as GeolocationPosition);
            },
            watchPosition: (success: PositionCallback, error?: PositionErrorCallback, options?: PositionOptions) => {
                success({
                    coords: {
                        latitude: mockCords.latitude,
                        longitude: mockCords.longitude,
                        accuracy: 10, altitude: null, altitudeAccuracy: null, heading: null, speed: null,
                    } as unknown as GeolocationCoordinates,
                    timestamp: Date.now()
                } as unknown as GeolocationPosition);
                return Math.floor(Math.random() * 10000);
            },
            clearWatch: (id: number) => {}
        };

        Object.defineProperty(navigator, 'geolocation', {
            value: mockGeolocation,
            configurable: true
        });

        return restoreGeo;
    }, [geoMock]);

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
                <h4 className={cn("font-bold text-xs mb-2 flex items-center gap-2", isDark ? "text-neon-cyan drop-shadow-[0_0_5px_rgba(0,255,255,0.8)]" : "text-blue-700")}>
                    <Globe2 className="w-4 h-4" /> Environment Scan
                </h4>
                <div className="space-y-1 mt-3">
                    <div className="flex justify-between text-[10px]">
                        <span className={isDark ? "text-gray-400" : "text-slate-500"}>Cookies</span>
                        <span className={cn("font-bold", isDark ? "text-green-400" : "text-green-600")}>{typeof window !== 'undefined' && navigator.cookieEnabled ? "ENABLED" : "DISABLED"}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                        <span className={isDark ? "text-gray-400" : "text-slate-500"}>Browser Status</span>
                        <span className={cn("font-bold", isDark ? "text-green-400" : "text-green-600")}>{typeof window !== 'undefined' && navigator.onLine ? "ONLINE" : "OFFLINE"}</span>
                    </div>
                </div>
            </div>

            {/* Network Throttling Simulator */}
            <div className={cn("p-4 border rounded flex flex-col gap-3 mt-4", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-yellow-400" : "text-yellow-600")}>
                        {netThrottle === "offline" ? <WifiOff className="w-4 h-4" /> : <Gauge className="w-4 h-4" />} Network Throttling
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        Intercepts `window.fetch` to simulate slow networks or offline states without disconnecting the OS.
                    </p>
                </div>
                
                <div className="flex gap-2 flex-wrap">
                    {[
                        { id: "none", label: "No Throttling" },
                        { id: "fast3g", label: "Fast 3G" },
                        { id: "slow3g", label: "Slow 3G" },
                        { id: "offline", label: "Offline" }
                    ].map(preset => (
                        <button
                            key={preset.id}
                            onClick={() => setNetThrottle(preset.id as any)}
                            className={cn(
                                "px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider border transition-all",
                                netThrottle === preset.id
                                    ? (isDark ? "bg-yellow-500/20 text-yellow-300 border-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.4)]" : "bg-yellow-100 text-yellow-700 border-yellow-500")
                                    : (isDark ? "bg-gray-900 border-gray-700 text-gray-400 hover:border-yellow-500/50 hover:text-yellow-400" : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100")
                            )}
                        >
                            {preset.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* GPS Mocker */}
            <div className={cn("p-4 border rounded flex flex-col gap-3 mt-4 mb-4", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-blue-400" : "text-blue-600")}>
                        <MapPin className="w-4 h-4" /> GPS Geolocation Spoofer
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        Overrides `navigator.geolocation` to spoof coordinate requests across the application.
                    </p>
                </div>
                
                <div className="flex gap-2 flex-wrap">
                    {[
                        { id: "real", label: "Real GPS" },
                        { id: "ny", label: "New York, USA" },
                        { id: "tokyo", label: "Tokyo, JP" },
                        { id: "london", label: "London, UK" },
                        { id: "null", label: "Null Island (0,0)" }
                    ].map(preset => (
                        <button
                            key={preset.id}
                            onClick={() => setGeoMock(preset.id as any)}
                            className={cn(
                                "px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider border transition-all",
                                geoMock === preset.id
                                    ? (isDark ? "bg-blue-500/20 text-blue-300 border-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.4)]" : "bg-blue-100 text-blue-700 border-blue-500")
                                    : (isDark ? "bg-gray-900 border-gray-700 text-gray-400 hover:border-blue-500/50 hover:text-blue-400" : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100")
                            )}
                        >
                            {preset.label}
                        </button>
                    ))}
                </div>
            </div>

        </div>
    );
}
