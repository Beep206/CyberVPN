import React, { useState, useEffect } from 'react';
import { Database, Trash2, RefreshCw, Key, HardDrive, Activity, Download } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';

type StorageItem = {
    key: string;
    value: string;
    size: number;
};

export function StorageTab({ isDark }: { isDark: boolean }) {
    const [localData, setLocalData] = useState<StorageItem[]>([]);
    const [sessionData, setSessionData] = useState<StorageItem[]>([]);
    const [cookieData, setCookieData] = useState<StorageItem[]>([]);
    const [indexedData, setIndexedData] = useState<StorageItem[]>([]);
    const [activeView, setActiveView] = useState<'local' | 'session' | 'cookies' | 'indexed'>('local');

    const loadIndexedDB = async () => {
        if (!window.indexedDB || !window.indexedDB.databases) return [];
        try {
            const dbs = await window.indexedDB.databases();
            const results: StorageItem[] = [];
            
            // Note: In Chrome/Edge, databases() returns {name, version}.
            // We can't trivially dump all object stores without opening them.
            // For a dev panel, we'll list the database names as keys.
            for (const db of dbs) {
                if (db.name) {
                    results.push({
                        key: db.name,
                        value: `Version: ${db.version}`,
                        size: 0 // Cannot easily calculate IDB size synchronously
                    });
                }
            }
            return results;
        } catch (e) {
            console.error("[Dev] IDB access error", e);
            return [];
        }
    };

    const loadData = async () => {
        if (typeof window === 'undefined') return;

        // Local Storage
        const lData: StorageItem[] = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key) {
                const value = localStorage.getItem(key) || '';
                lData.push({ key, value, size: new Blob([value]).size });
            }
        }
        setLocalData(lData.sort((a, b) => a.key.localeCompare(b.key)));

        // Session Storage
        const sData: StorageItem[] = [];
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key) {
                const value = sessionStorage.getItem(key) || '';
                sData.push({ key, value, size: new Blob([value]).size });
            }
        }
        setSessionData(sData.sort((a, b) => a.key.localeCompare(b.key)));

        // Cookies
        const cData: StorageItem[] = [];
        const cookies = document.cookie.split(';');
        cookies.forEach(c => {
            const [key, ...v] = c.split('=');
            if (key) {
                const value = v.join('=');
                cData.push({ key: key.trim(), value: value.trim(), size: new Blob([value]).size });
            }
        });
        setCookieData(cData.filter(c => c.key).sort((a, b) => a.key.localeCompare(b.key)));

        // IndexedDB
        const idbData = await loadIndexedDB();
        setIndexedData(idbData.sort((a, b) => a.key.localeCompare(b.key)));
    };

    useEffect(() => {
        loadData();
    }, []);

    const handleDelete = (key: string, type: 'local' | 'session' | 'cookies' | 'indexed') => {
        if (type === 'local') localStorage.removeItem(key);
        if (type === 'session') sessionStorage.removeItem(key);
        if (type === 'cookies') document.cookie = `${key}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
        if (type === 'indexed') {
            const req = window.indexedDB.deleteDatabase(key);
            req.onsuccess = () => loadData();
            req.onerror = () => alert(`Failed to delete IDB: ${key}`);
            return; // loadData is called in onsuccess
        }
        loadData();
    };

    const handleNukeAll = () => {
        if (confirm("WARNING: This will delete ALL localStorage, sessionStorage, cookies, and IndexedDBs for this domain. You will be logged out and all dev panel settings will reset. Continue?")) {
            localStorage.clear();
            sessionStorage.clear();
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i];
                const eqPos = cookie.indexOf("=");
                const name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
                document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
            }
            indexedData.forEach(db => window.indexedDB.deleteDatabase(db.key));
            setTimeout(() => window.location.reload(), 500);
        }
    };

    const exportStateDump = () => {
        const dump = {
            localStorage: Object.fromEntries(localData.map(i => [i.key, i.value])),
            sessionStorage: Object.fromEntries(sessionData.map(i => [i.key, i.value])),
            cookies: Object.fromEntries(cookieData.map(i => [i.key, i.value])),
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent
        };
        
        const blob = new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cybervpn-state-dump-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '---'; // IDB size unknown usually
        if (bytes < 1024) return bytes + ' B';
        return (bytes / 1024).toFixed(1) + ' KB';
    };

    const getCurrentData = () => {
        if (activeView === 'local') return localData;
        if (activeView === 'session') return sessionData;
        if (activeView === 'indexed') return indexedData;
        return cookieData;
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-neon-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.8)]" : "text-blue-700")}>
                    <Database className="w-5 h-5" /> Storage Manager
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={exportStateDump}
                        className={cn(
                            "p-1.5 rounded transition-all flex items-center gap-1 text-[10px] font-bold uppercase",
                            isDark ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/40 border border-emerald-500/30" : "bg-emerald-100 text-emerald-600 hover:bg-emerald-200"
                        )}
                        title="Export State JSON"
                    >
                        <Download className="w-3.5 h-3.5" /> Export Dump
                    </button>
                    <button
                        onClick={loadData}
                        className={cn(
                            "p-1.5 rounded transition-all flex items-center gap-1 text-[10px] font-bold uppercase",
                            isDark ? "hover:bg-gray-800 text-neon-cyan" : "hover:bg-blue-100 text-blue-600"
                        )}
                        title="Refresh Data"
                    >
                        <RefreshCw className="w-3.5 h-3.5" /> Refresh
                    </button>
                    <button
                        onClick={handleNukeAll}
                        className={cn(
                            "p-1.5 rounded transition-all flex items-center gap-1 text-[10px] font-bold uppercase",
                            isDark ? "bg-red-500/20 text-red-400 hover:bg-red-500/40 border border-red-500/30" : "bg-red-100 text-red-600 hover:bg-red-200"
                        )}
                    >
                        <Trash2 className="w-3.5 h-3.5" /> NUKE ALL
                    </button>
                </div>
            </div>

            {/* Sub-tabs */}
            <div className="flex border-b border-gray-700/50 mb-4 overflow-x-auto">
                {(['local', 'session', 'cookies', 'indexed'] as const).map(view => (
                    <button
                        key={view}
                        onClick={() => setActiveView(view)}
                        className={cn(
                            "px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors relative shrink-0",
                            activeView === view
                                ? (isDark ? "text-neon-cyan" : "text-blue-600")
                                : (isDark ? "text-gray-500 hover:text-gray-300" : "text-slate-500 hover:text-slate-700")
                        )}
                    >
                        {view === 'local' && <HardDrive className="inline w-3 h-3 mr-1" />}
                        {view === 'session' && <Activity className="inline w-3 h-3 mr-1" />}
                        {view === 'cookies' && <Key className="inline w-3 h-3 mr-1" />}
                        {view === 'indexed' && <Database className="inline w-3 h-3 mr-1" />}
                        {view}
                        {activeView === view && (
                            <motion.div
                                layoutId="storageTabIndicator"
                                className={cn("absolute bottom-0 left-0 right-0 h-0.5", isDark ? "bg-neon-cyan" : "bg-blue-600")}
                            />
                        )}
                    </button>
                ))}
            </div>

            {/* Data Table */}
            <div className={cn("flex-1 overflow-auto border rounded relative", isDark ? "border-gray-800 bg-black/40" : "border-slate-200 bg-white")}>
                <table className="w-full text-left border-collapse text-xs">
                    <thead className={cn("sticky top-0 z-10", isDark ? "bg-gray-900 border-b border-gray-800" : "bg-slate-100 border-b border-slate-200")}>
                        <tr>
                            <th className="p-2 font-semibold">Key</th>
                            <th className="p-2 font-semibold">Value</th>
                            <th className="p-2 font-semibold w-20">Size</th>
                            <th className="p-2 font-semibold w-12 text-center">Act</th>
                        </tr>
                    </thead>
                    <tbody>
                        {getCurrentData().length === 0 ? (
                            <tr>
                                <td colSpan={4} className={cn("p-8 text-center italic", isDark ? "text-gray-600" : "text-slate-400")}>
                                    No data found in {activeView}.
                                </td>
                            </tr>
                        ) : (
                            getCurrentData().map((item) => (
                                <tr key={item.key} className={cn("border-b last:border-0", isDark ? "border-gray-800 hover:bg-gray-800/50" : "border-slate-100 hover:bg-slate-50")}>
                                    <td className="p-2 font-mono break-all text-[11px] align-top w-1/3">
                                        <div className={isDark ? "text-neon-pink" : "text-pink-600"}>{item.key}</div>
                                    </td>
                                    <td className="p-2 font-mono text-[10px] break-all align-top">
                                        <div className={cn("max-h-20 overflow-y-auto whitespace-pre-wrap", isDark ? "text-gray-300" : "text-slate-600")}>
                                            {item.value || <span className="text-gray-500 italic">Empty</span>}
                                        </div>
                                    </td>
                                    <td className="p-2 text-[10px] align-top opacity-70">
                                        {formatSize(item.size)}
                                    </td>
                                    <td className="p-2 text-center align-top">
                                        <button
                                            onClick={() => handleDelete(item.key, activeView)}
                                            className={cn("p-1 rounded transition-colors", isDark ? "hover:bg-red-500/20 text-gray-500 hover:text-red-400" : "hover:bg-red-100 text-slate-400 hover:text-red-500")}
                                            title="Delete Item"
                                        >
                                            <Trash2 className="w-3.5 h-3.5 mx-auto" />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            
            <div className={cn("text-[10px] flex justify-between", isDark ? "text-gray-500" : "text-slate-500")}>
                <span>Total Items: {getCurrentData().length}</span>
                <span>Used: {formatSize(getCurrentData().reduce((acc, item) => acc + item.size, 0))}</span>
            </div>
        </div>
    );
}
