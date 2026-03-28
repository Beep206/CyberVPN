import React, { useState, useEffect } from "react";
import { Activity, Trash2, ChevronDown, ChevronRight, Terminal, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { networkLogger, NetworkLogEntry } from "../lib/network-logger";

export function NetworkTab({ isDark }: { isDark: boolean }) {
    const [logs, setLogs] = useState<NetworkLogEntry[]>([]);
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
    const [isRecording, setIsRecording] = useState(true);

    useEffect(() => {
        // Start intercepting when tab is mounted, or just rely on dev-panel mounting it
        // We'll toggle it on mount
        networkLogger.start();

        const unsubscribe = networkLogger.subscribe(setLogs);
        return () => {
            unsubscribe();
            // Optional: stop logging when tab is closed to save memory
            // networkLogger.stop();
        };
    }, []);

    const toggleExpand = (id: string) => {
        const next = new Set(expandedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setExpandedIds(next);
    };

    const clearLogs = () => {
        networkLogger.clear();
    };

    const getStatusColor = (status?: number) => {
        if (!status) return isDark ? "text-gray-400" : "text-gray-500";
        if (status >= 200 && status < 300) return isDark ? "text-neon-cyan" : "text-green-500";
        if (status >= 400 && status < 500) return isDark ? "text-yellow-400" : "text-orange-500";
        return isDark ? "text-neon-pink" : "text-red-500";
    };

    const exportAsCurl = (log: NetworkLogEntry) => {
        let curl = `curl '${log.url}' \\\n  -X '${log.method}' \\\n`;
        
        const headers = { ...log.reqHeaders };
        // If it's a replay, we want to try to keep it close to original
        Object.entries(headers).forEach(([key, val]) => {
            if (val) curl += `  -H '${key}: ${val}' \\\n`;
        });

        if (log.reqBody) {
            const bodyStr = typeof log.reqBody === 'object' ? JSON.stringify(log.reqBody) : String(log.reqBody);
            // Escape single quotes for bash
            curl += `  --data-raw '${bodyStr.replace(/'/g, "'\\''")}' \\\n`;
        }

        // Remove trailing slash and newline
        curl = curl.trim().replace(/\\\n$/, '').trim();
        if (curl.endsWith('\\')) curl = curl.slice(0, -1).trim();

        navigator.clipboard.writeText(curl);
        
        // Brief visual feedback (could use a toast here if configured, or just console)
        console.log('[Dev Tools] Copied cURL to clipboard:\n', curl);
        alert('Copied cURL to clipboard!');
    };

    const replayRequest = async (log: NetworkLogEntry, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            const options: RequestInit = {
                method: log.method,
                headers: log.reqHeaders as HeadersInit,
            };
            if (log.method !== 'GET' && log.method !== 'HEAD' && log.reqBody) {
                options.body = typeof log.reqBody === 'object' ? JSON.stringify(log.reqBody) : String(log.reqBody);
            }
            // Fetch triggers the interceptor natively, so it will appear at the top of the logs
            await fetch(log.url, options);
        } catch (err) {
            console.error('[Dev Tools] Replay failed', err);
        }
    };

    return (
        <div className="space-y-4 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan to-blue-500 drop-shadow-[0_0_8px_rgba(0,255,255,0.8)]" : "text-slate-800")}>Network Monitor</h3>
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 mr-2">
                        <span className={cn("relative flex h-2.5 w-2.5")}>
                            {isRecording && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>}
                            <span className={cn("relative inline-flex rounded-full h-2.5 w-2.5", isRecording ? "bg-red-500" : "bg-gray-500")}></span>
                        </span>
                        <span className={cn("text-xs font-bold", isDark ? "text-gray-400" : "text-slate-500")}>
                            {isRecording ? "REC" : "PAUSED"}
                        </span>
                    </div>
                    <button
                        onClick={clearLogs}
                        title="Clear logs"
                        className={cn(
                            "p-1.5 rounded transition-all",
                            isDark ? "hover:bg-red-900/40 text-red-400" : "hover:bg-red-100 text-red-500"
                        )}
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </div>

            <div className="border rounded overflow-hidden flex-1 overflow-y-auto" style={{ maxHeight: "calc(100vh - 250px)" }}>
                <table className="w-full text-left text-xs">
                    <thead className={cn("sticky top-0 z-10", isDark ? "bg-black/90 border-b border-gray-800" : "bg-slate-50 border-b border-slate-200")}>
                        <tr>
                            <th className="p-2 font-bold w-6"></th>
                            <th className="p-2 font-bold w-12">Method</th>
                            <th className="p-2 font-bold w-12">Status</th>
                            <th className="p-2 font-bold truncate max-w-[150px]">URL</th>
                            <th className="p-2 font-bold text-right w-16">Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.length === 0 ? (
                            <tr>
                                <td colSpan={5} className={cn("p-8 text-center", isDark ? "text-gray-500" : "text-slate-400")}>
                                    <Activity className="w-8 h-8 mx-auto mb-2 opacity-20" />
                                    No network activity recorded.
                                </td>
                            </tr>
                        ) : logs.map((log) => {
                            const isExpanded = expandedIds.has(log.id);
                            return (
                                <React.Fragment key={log.id}>
                                    <tr 
                                        onClick={() => toggleExpand(log.id)}
                                        className={cn(
                                            "cursor-pointer border-b transition-colors", 
                                            isDark ? "border-gray-900 hover:bg-gray-900/50" : "border-slate-100 hover:bg-slate-50",
                                            isExpanded && (isDark ? "bg-gray-900/30" : "bg-blue-50/50")
                                        )}
                                    >
                                        <td className="p-2">
                                            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                                        </td>
                                        <td className={cn("p-2 font-bold", isDark ? "text-gray-300" : "text-slate-700")}>{log.method}</td>
                                        <td className={cn("p-2 font-bold", getStatusColor(log.status))}>{log.status || "---"}</td>
                                        <td className="p-2 truncate max-w-[150px] font-mono text-[10px] break-all" title={log.url}>
                                            {log.url.split('?')[0].split('/').pop() || log.url}
                                        </td>
                                        <td className="p-2 text-right font-mono">{log.duration ? `${log.duration}ms` : '...'}</td>
                                    </tr>
                                    {isExpanded && (
                                        <tr className={cn("border-b", isDark ? "bg-black border-gray-900" : "bg-white border-slate-200")}>
                                            <td colSpan={5} className="p-4 text-[11px] font-mono whitespace-pre-wrap break-all relative">
                                                
                                                {/* Action Bar */}
                                                <div className="absolute top-4 right-4 flex gap-2">
                                                    <button 
                                                        onClick={() => exportAsCurl(log)}
                                                        className={cn(
                                                            "flex items-center gap-1.5 px-2 py-1 rounded border transition-colors",
                                                            isDark ? "border-gray-800 text-gray-400 hover:text-white hover:bg-gray-800" : "border-slate-300 text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                                                        )}
                                                    >
                                                        <Terminal className="w-3 h-3" /> cURL
                                                    </button>
                                                    <button 
                                                        onClick={(e) => replayRequest(log, e)}
                                                        className={cn(
                                                            "flex items-center gap-1.5 px-2 py-1 rounded border transition-colors text-blue-500",
                                                            isDark ? "border-blue-900/50 hover:bg-blue-900/30" : "border-blue-200 hover:bg-blue-50"
                                                        )}
                                                    >
                                                        <RefreshCw className="w-3 h-3" /> Replay
                                                    </button>
                                                </div>

                                                <div className="space-y-3 pr-40">
                                                    <div>
                                                        <span className={cn("font-bold", isDark ? "text-neon-cyan" : "text-blue-600")}>URL: </span>
                                                        <span className={isDark ? "text-gray-300" : "text-slate-600"}>{log.url}</span>
                                                    </div>
                                                    
                                                    {log.reqHeaders && Object.keys(log.reqHeaders).length > 0 && (
                                                        <div>
                                                            <span className={cn("font-bold block mb-1", isDark ? "text-neon-cyan" : "text-blue-600")}>Request Headers:</span>
                                                            <div className={cn("p-2 rounded overflow-auto max-h-24", isDark ? "bg-gray-950 text-gray-400" : "bg-slate-50 text-slate-500")}>
                                                                {JSON.stringify(log.reqHeaders, null, 2)}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {log.reqBody && (
                                                        <div>
                                                            <span className={cn("font-bold block mb-1", isDark ? "text-neon-cyan" : "text-blue-600")}>Request Body:</span>
                                                            <div className={cn("p-2 rounded overflow-auto max-h-32", isDark ? "bg-gray-950 text-gray-400" : "bg-slate-50 text-slate-500")}>
                                                                {typeof log.reqBody === 'object' ? JSON.stringify(log.reqBody, null, 2) : String(log.reqBody)}
                                                            </div>
                                                        </div>
                                                    )}

                                                    {log.resBody && (
                                                        <div>
                                                            <span className={cn("font-bold block mb-1", isDark ? "text-neon-pink" : "text-purple-600")}>Response Body:</span>
                                                            <div className={cn("p-2 rounded overflow-auto max-h-48", isDark ? "bg-gray-950 text-gray-400 shadow-[inset_0_0_10px_rgba(255,0,255,0.05)]" : "bg-slate-50 text-slate-500")}>
                                                                {typeof log.resBody === 'object' ? JSON.stringify(log.resBody, null, 2) : String(log.resBody)}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
