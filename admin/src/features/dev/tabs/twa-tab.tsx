import React, { useState, useEffect } from 'react';
import { Smartphone, MonitorPlay, Zap, ToggleLeft, ToggleRight, HardDrive, DollarSign, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';

type TwaMockConfig = {
    enabled: boolean;
    platform: 'android' | 'ios' | 'tdesktop' | 'weba' | 'webk' | 'macos';
    theme: 'light' | 'dark';
    user: {
        id: number;
        first_name: string;
        last_name: string;
        username: string;
        language_code: string;
        is_premium: boolean;
    };
};

const DEFAULT_CONFIG: TwaMockConfig = {
    enabled: false,
    platform: 'ios',
    theme: 'dark',
    user: {
        id: 12345678,
        first_name: 'John',
        last_name: 'Doe',
        username: 'johndoe',
        language_code: 'en',
        is_premium: true
    }
};

export function TwaTab({ isDark }: { isDark: boolean }) {
    const [config, setConfig] = useState<TwaMockConfig>(DEFAULT_CONFIG);
    const [events, setEvents] = useState<{ id: string; time: Date; type: string; payload: string }[]>([]);

    const logEvent = (type: string, payload: string) => {
        setEvents(prev => [{ id: Math.random().toString(36).substring(7), time: new Date(), type, payload }, ...prev].slice(0, 50));
    };

    // Attach to global scope for the mock to call
    useEffect(() => {
        (window as any).__DEV_TWA_LOG__ = logEvent;
    }, []);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('DEV_TWA_MOCK');
            if (saved) {
                try { setConfig(JSON.parse(saved)); } catch { /* ignore */ }
            }
        }
    }, []);

    const updateConfig = (updates: Partial<TwaMockConfig>) => {
        const next = { ...config, ...updates };
        setConfig(next);
        if (typeof window !== 'undefined') {
            localStorage.setItem('DEV_TWA_MOCK', JSON.stringify(next));
        }
    };

    const updateUserData = (updates: Partial<TwaMockConfig['user']>) => {
        updateConfig({ user: { ...config.user, ...updates } });
    };

    const injectMock = () => {
        if (typeof window === 'undefined') return;
        
        // This is a naive injection useful for Next.js hydration before @twa-dev/sdk loads
        // It patches the global window.Telegram object.
        const mockInitDataUnsafe = {
            query_id: "mock_query_id",
            user: config.user,
            auth_date: Math.floor(Date.now() / 1000),
            hash: "mock_hash"
        };
        
        const mockInitData = new URLSearchParams({
            query_id: mockInitDataUnsafe.query_id,
            user: JSON.stringify(mockInitDataUnsafe.user),
            auth_date: mockInitDataUnsafe.auth_date.toString(),
            hash: mockInitDataUnsafe.hash
        }).toString();

        (window as any).Telegram = {
            WebApp: {
                initData: mockInitData,
                initDataUnsafe: mockInitDataUnsafe,
                version: '7.0',
                platform: config.platform,
                colorScheme: config.theme,
                themeParams: {
                    bg_color: config.theme === 'dark' ? '#000000' : '#ffffff',
                    text_color: config.theme === 'dark' ? '#ffffff' : '#000000',
                    hint_color: '#a8a8a8',
                    link_color: '#3390ec',
                    button_color: '#3390ec',
                    button_text_color: '#ffffff',
                    secondary_bg_color: config.theme === 'dark' ? '#1c1c1d' : '#f0f0f0',
                },
                isExpanded: true,
                viewportHeight: window.innerHeight,
                viewportStableHeight: window.innerHeight,
                headerColor: '#000000',
                backgroundColor: '#000000',
                BackButton: {
                    isVisible: false,
                    onClick: () => {},
                    show: () => {},
                    hide: () => {}
                },
                MainButton: {
                    text: 'CONTINUE',
                    color: '#3390ec',
                    textColor: '#ffffff',
                    isVisible: false,
                    isActive: true,
                    isProgressVisible: false,
                    setParams: () => {},
                    onClick: () => {},
                    show: () => {},
                    hide: () => {},
                    enable: () => {},
                    disable: () => {},
                    showProgress: () => {},
                    hideProgress: () => {}
                },
                HapticFeedback: {
                    impactOccurred: (style: string) => (window as any).__DEV_TWA_LOG__?.('HAPTIC_IMPACT', style),
                    notificationOccurred: (type: string) => (window as any).__DEV_TWA_LOG__?.('HAPTIC_NOTIFICATION', type),
                    selectionChanged: () => (window as any).__DEV_TWA_LOG__?.('HAPTIC_SELECTION', 'changed')
                },
                CloudStorage: {
                    setItem: (key: string, value: string, cb?: (err: any, ok: boolean) => void) => {
                        (window as any).__DEV_TWA_LOG__?.('CLOUD_SET', `${key}=${value.substring(0,20)}...`);
                        localStorage.setItem(`TWA_CLOUD_${key}`, value);
                        if(cb) cb(null, true);
                    },
                    getItem: (key: string, cb?: (err: any, val: string) => void) => {
                        const val = localStorage.getItem(`TWA_CLOUD_${key}`) || '';
                        (window as any).__DEV_TWA_LOG__?.('CLOUD_GET', `${key}=${val.substring(0,20)}...`);
                        if(cb) cb(null, val);
                    },
                    getItems: (keys: string[], cb?: (err: any, vals: Record<string, string>) => void) => {
                        (window as any).__DEV_TWA_LOG__?.('CLOUD_GET_MULTI', keys.join(','));
                        const res: Record<string, string> = {};
                        keys.forEach(k => res[k] = localStorage.getItem(`TWA_CLOUD_${k}`) || '');
                        if(cb) cb(null, res);
                    },
                    removeItem: (key: string, cb?: (err: any, ok: boolean) => void) => {
                        (window as any).__DEV_TWA_LOG__?.('CLOUD_REMOVE', key);
                        localStorage.removeItem(`TWA_CLOUD_${key}`);
                        if(cb) cb(null, true);
                    },
                    removeItems: (keys: string[], cb?: (err: any, ok: boolean) => void) => {
                        (window as any).__DEV_TWA_LOG__?.('CLOUD_REMOVE_MULTI', keys.join(','));
                        keys.forEach(k => localStorage.removeItem(`TWA_CLOUD_${k}`));
                        if(cb) cb(null, true);
                    },
                    getKeys: (cb?: (err: any, keys: string[]) => void) => {
                        const keys: string[] = [];
                        for(let i=0; i<localStorage.length; i++) {
                            const k = localStorage.key(i);
                            if(k?.startsWith('TWA_CLOUD_')) keys.push(k.replace('TWA_CLOUD_', ''));
                        }
                        (window as any).__DEV_TWA_LOG__?.('CLOUD_KEYS', keys.join(','));
                        if(cb) cb(null, keys);
                    }
                },
                openInvoice: (url: string, callback?: (status: string) => void) => {
                    (window as any).__DEV_TWA_LOG__?.('INVOICE_OPENED', url);
                    if (confirm(`Simulate successful payment for invoice?\nURL: ${url}`)) {
                        (window as any).__DEV_TWA_LOG__?.('INVOICE_STATUS', 'paid');
                        if(callback) callback('paid');
                    } else if (confirm('Simulate failed payment? (Click Cancel for cancelled)')) {
                        (window as any).__DEV_TWA_LOG__?.('INVOICE_STATUS', 'failed');
                        if(callback) callback('failed');
                    } else {
                        (window as any).__DEV_TWA_LOG__?.('INVOICE_STATUS', 'cancelled');
                        if(callback) callback('cancelled');
                    }
                },
                ready: () => (window as any).__DEV_TWA_LOG__?.('SYSTEM', 'WebApp.ready() called'),
                expand: () => (window as any).__DEV_TWA_LOG__?.('SYSTEM', 'WebApp.expand() called'),
                close: () => (window as any).__DEV_TWA_LOG__?.('SYSTEM', 'WebApp.close() called'),
            }
        };

        // Reload to apply mock @twa-dev/sdk reads window.Telegram on initialization
        window.location.reload();
    };

    const removeMock = () => {
        if (typeof window === 'undefined') return;
        updateConfig({ enabled: false });
        delete (window as any).Telegram;
        window.location.reload();
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-sky-400 drop-shadow-[0_0_8px_rgba(56,189,248,0.8)]" : "text-sky-600")}>
                    <Smartphone className="w-5 h-5 text-sky-500" /> TWA Emulator
                </h3>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                Injects a mocked `window.Telegram` object to simulate Telegram Mini App user payloads and context inside the desktop browser. Requires a page reload.
            </p>

            {/* Master Toggle */}
            <div className={cn("p-4 border rounded flex items-center justify-between", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-sky-400" : "text-sky-600")}>
                        <Zap className="w-4 h-4" /> Mock Active Environment
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        {config.enabled ? "TWA context is currently mocking." : "Native browser context."}
                    </p>
                </div>
                {config.enabled ? (
                    <button onClick={removeMock} className={cn("relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2", isDark ? "bg-sky-500/30 border-sky-500 shadow-[0_0_15px_rgba(56,189,248,0.4)]" : "bg-sky-100 border-sky-500")}>
                         <div className={cn("absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300", isDark ? "translate-x-6 bg-sky-400 shadow-[0_0_10px_#38bdf8]" : "translate-x-6 bg-sky-500")} />
                    </button>
                ) : (
                    <button onClick={() => { updateConfig({ enabled: true }); injectMock(); }} className={cn("relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2", isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")}>
                         <div className={cn("absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300", isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")} />
                    </button>
                )}
            </div>

            {/* Config Form */}
            <div className={cn("flex-1 overflow-auto p-4 border rounded space-y-4", isDark ? "bg-black/30 border-gray-800" : "bg-slate-50/50 border-slate-200")}>
                
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Platform</label>
                        <select
                            value={config.platform}
                            onChange={e => updateConfig({ platform: e.target.value as any })}
                            className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-gray-900 border-gray-700 focus:border-sky-500 text-white" : "bg-white border-slate-300")}
                        >
                            <option value="ios">iOS</option>
                            <option value="android">Android</option>
                            <option value="tdesktop">Desktop</option>
                            <option value="macos">macOS</option>
                            <option value="weba">Web A</option>
                            <option value="webk">Web K</option>
                        </select>
                    </div>
                    <div className="space-y-1">
                        <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Client Theme</label>
                        <select
                            value={config.theme}
                            onChange={e => updateConfig({ theme: e.target.value as any })}
                            className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-gray-900 border-gray-700 focus:border-sky-500 text-white" : "bg-white border-slate-300")}
                        >
                            <option value="dark">Dark</option>
                            <option value="light">Light</option>
                        </select>
                    </div>
                </div>

                <div className="pt-2 border-t border-gray-800/50">
                    <h4 className={cn("font-bold text-xs uppercase mb-3", isDark ? "text-gray-300" : "text-slate-600")}>User Payload (initDataUnsafe)</h4>
                    
                    <div className="grid grid-cols-2 gap-4 mb-3">
                        <div className="space-y-1">
                            <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>User ID</label>
                            <input 
                                type="number" 
                                value={config.user.id} 
                                onChange={e => updateUserData({ id: parseInt(e.target.value) || 0 })}
                                className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700 focus:border-sky-500 text-sky-400" : "bg-white border-slate-300 focus:border-sky-500 text-sky-600")}
                            />
                        </div>
                        <div className="space-y-1">
                            <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Username</label>
                            <input 
                                type="text" 
                                value={config.user.username} 
                                onChange={e => updateUserData({ username: e.target.value })}
                                className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700 focus:border-sky-500" : "bg-white border-slate-300")}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-3">
                        <div className="space-y-1">
                            <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>First Name</label>
                            <input 
                                type="text" 
                                value={config.user.first_name} 
                                onChange={e => updateUserData({ first_name: e.target.value })}
                                className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700 focus:border-sky-500" : "bg-white border-slate-300")}
                            />
                        </div>
                        <div className="space-y-1">
                            <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Last Name</label>
                            <input 
                                type="text" 
                                value={config.user.last_name} 
                                onChange={e => updateUserData({ last_name: e.target.value })}
                                className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700 focus:border-sky-500" : "bg-white border-slate-300")}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex items-center gap-3 mt-2">
                             <button
                                onClick={() => updateUserData({ is_premium: !config.user.is_premium })}
                                className={cn(
                                    "p-1.5 rounded transition-colors",
                                    config.user.is_premium
                                        ? (isDark ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" : "bg-purple-100 text-purple-600 border border-purple-200")
                                        : (isDark ? "bg-gray-800 text-gray-500" : "bg-slate-200 text-slate-400")
                                )}
                            >
                                <Zap className={cn("w-4 h-4", config.user.is_premium && "fill-current")} />
                            </button>
                            <span className={cn("text-xs font-bold uppercase", isDark ? "text-gray-300" : "text-slate-600")}>Premium Active</span>
                        </div>
                        <div className="space-y-1">
                            <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Language</label>
                            <input 
                                type="text" 
                                value={config.user.language_code} 
                                onChange={e => updateUserData({ language_code: e.target.value })}
                                className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none uppercase", isDark ? "bg-black border-gray-700 focus:border-sky-500" : "bg-white border-slate-300")}
                                maxLength={2}
                            />
                        </div>
                    </div>
                </div>

                <div className="pt-4">
                    <button 
                        onClick={() => { updateConfig({ enabled: true }); injectMock(); }}
                        className={cn(
                            "w-full py-2 flex items-center justify-center gap-2 rounded text-xs font-bold uppercase tracking-widest transition-all",
                            isDark 
                                ? "bg-sky-600 hover:bg-sky-500 text-white shadow-[0_0_15px_rgba(56,189,248,0.3)]" 
                                : "bg-sky-500 hover:bg-sky-600 text-white shadow-md"
                        )}
                    >
                        Save & Reload Context
                    </button>
                </div>
            </div>

            {/* Event Log */}
            <div className={cn("flex-1 overflow-hidden border rounded flex flex-col min-h-[150px]", isDark ? "bg-black/30 border-gray-800" : "bg-slate-50/50 border-slate-200")}>
                <div className={cn("p-2 border-b flex justify-between items-center", isDark ? "bg-gray-900 border-gray-800" : "bg-slate-100 border-slate-200")}>
                    <h4 className={cn("font-bold text-[10px] uppercase flex items-center gap-2", isDark ? "text-gray-400" : "text-slate-500")}>
                        <Activity className="w-3.5 h-3.5" /> SDK Event Log
                    </h4>
                    <button onClick={() => setEvents([])} className={cn("text-[9px] uppercase font-bold px-2 py-0.5 rounded", isDark ? "bg-gray-800 text-gray-400 hover:text-white" : "bg-white border text-slate-500 hover:text-slate-800")}>
                        Clear
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {events.length === 0 ? (
                        <div className="h-full flex items-center justify-center italic text-xs opacity-30">
                            Waiting for WebApp calls...
                        </div>
                    ) : (
                        events.map(ev => (
                            <div key={ev.id} className="text-[10px] font-mono flex gap-2 border-b border-dashed border-gray-700/30 pb-1">
                                <span className="opacity-50 shrink-0">{ev.time.toLocaleTimeString([], { hour12: false })}</span>
                                <span className={cn("font-bold shrink-0", 
                                    ev.type.includes('HAPTIC') ? (isDark ? 'text-pink-400' : 'text-pink-600') :
                                    ev.type.includes('CLOUD') ? (isDark ? 'text-cyan-400' : 'text-cyan-600') :
                                    ev.type.includes('INVOICE') ? (isDark ? 'text-green-400' : 'text-green-600') :
                                    (isDark ? 'text-gray-400' : 'text-gray-600')
                                )}>{ev.type}</span>
                                <span className="text-gray-400 truncate break-all">{ev.payload}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>

        </div>
    );
}
