import React, { useState, useEffect } from 'react';
import { Languages, AlignRight, Key } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePathname, useRouter } from '@/i18n/navigation';
import { useLocale } from 'next-intl';
import { locales } from '@/i18n/config';

export function I18nTab({ isDark }: { isDark: boolean }) {
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();
    const [forceRtl, setForceRtl] = useState(false);
    const [showKeys, setShowKeys] = useState(false);

    useEffect(() => {
        setForceRtl(document.documentElement.dir === 'rtl');
        setShowKeys(document.cookie.includes('DEV_SHOW_KEYS=true'));
    }, []);

    const toggleRtl = () => {
        const next = !forceRtl;
        setForceRtl(next);
        document.documentElement.dir = next ? 'rtl' : 'ltr';
        if (typeof window !== 'undefined') {
            localStorage.setItem('DEV_RTL', next ? 'true' : 'false');
        }
    };

    const toggleShowKeys = () => {
        const next = !showKeys;
        if (next) {
            document.cookie = "DEV_SHOW_KEYS=true; path=/; max-age=31536000";
        } else {
            document.cookie = "DEV_SHOW_KEYS=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        }
        setShowKeys(next);
        window.location.reload();
    };

    const handleLocaleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        router.replace(pathname, { locale: e.target.value as any });
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500 drop-shadow-[0_0_8px_rgba(0,0,255,0.8)]" : "text-blue-700")}>
                    <Languages className="w-5 h-5 text-blue-500" /> i18n Debugger
                </h3>
            </div>

            <div className={cn("p-4 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <h4 className={cn("font-bold flex items-center gap-2 mb-2", isDark ? "text-blue-400" : "text-blue-600")}>
                    <Languages className="w-4 h-4" /> Quick Switch Locale
                </h4>
                <p className={cn("text-xs mb-3", isDark ? "text-gray-400" : "text-slate-500")}>Switch the current application locale without changing the URL manually.</p>
                <select 
                    value={locale} 
                    onChange={handleLocaleChange}
                    className={cn(
                        "w-full p-2 text-sm font-mono border rounded outline-none transition-colors",
                        isDark ? "bg-gray-900 border-gray-700 text-neon-cyan focus:border-neon-cyan" : "bg-slate-50 border-slate-300 focus:border-blue-500 text-slate-800"
                    )}
                >
                    {locales.map((l: string) => (
                        <option key={l} value={l}>{l}</option>
                    ))}
                </select>
            </div>

            <div className={cn("p-4 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-purple-400" : "text-purple-600")}>
                            <Key className="w-4 h-4" /> Show Translation Keys
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Force the app to render keys (e.g., `Dashboard.title`) to spot missing strings.</p>
                    </div>
                    <button
                        onClick={toggleShowKeys}
                        className={cn(
                            "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                            showKeys
                                ? (isDark ? "bg-purple-500/30 border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.4)]" : "bg-purple-100 border-purple-500")
                                : (isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")
                        )}
                    >
                        <div
                            className={cn(
                                "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                                showKeys
                                    ? (isDark ? "translate-x-6 bg-purple-400 shadow-[0_0_10px_#a855f7]" : "translate-x-6 bg-purple-500")
                                    : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                            )}
                        />
                    </button>
                </div>
            </div>

            <div className={cn("p-4 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex items-center justify-between">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-indigo-400" : "text-indigo-600")}>
                            <AlignRight className="w-4 h-4" /> Force RTL Layout
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Injects `dir="rtl"` into the HTML tag to test right-to-left layout rendering immediately.</p>
                    </div>
                    <button
                        onClick={toggleRtl}
                        className={cn(
                            "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                            forceRtl
                                ? (isDark ? "bg-indigo-500/30 border-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.4)]" : "bg-indigo-100 border-indigo-500")
                                : (isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")
                        )}
                    >
                        <div
                            className={cn(
                                "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                                forceRtl
                                    ? (isDark ? "translate-x-6 bg-indigo-400 shadow-[0_0_10px_#818cf8]" : "translate-x-6 bg-indigo-500")
                                    : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                            )}
                        />
                    </button>
                </div>
            </div>

        </div>
    );
}
