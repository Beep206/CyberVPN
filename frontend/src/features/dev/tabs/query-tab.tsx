import React, { useState, useEffect } from 'react';
import { DatabaseZap, RefreshCw, Trash2, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'motion/react';

type QueryInfo = {
    queryKey: string;
    queryHash: string;
    state: any;
    status: 'pending' | 'error' | 'success';
    fetchStatus: 'fetching' | 'paused' | 'idle';
    dataUpdatedAt: number;
    staleTime: number;
    subscribers: number;
};

export function QueryTab({ isDark }: { isDark: boolean }) {
    const queryClient = useQueryClient();
    const [queries, setQueries] = useState<QueryInfo[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
    const [editData, setEditData] = useState<Record<string, string>>({});

    const updateQueries = () => {
        if (!queryClient) return;
        const cache = queryClient.getQueryCache();
        const all = cache.getAll().map(q => ({
            queryKey: JSON.stringify(q.queryKey),
            queryHash: q.queryHash,
            state: q.state,
            status: q.state.status,
            fetchStatus: q.state.fetchStatus,
            dataUpdatedAt: q.state.dataUpdatedAt,
            staleTime: (q as any).options?.staleTime || 0,
            subscribers: q.getObserversCount()
        }));
        
        // Sort by most recently updated
        all.sort((a, b) => b.dataUpdatedAt - a.dataUpdatedAt);
        setQueries(all);
    };

    useEffect(() => {
        updateQueries();
        // Subscribe to cache changes
        if (queryClient) {
            const unsubscribe = queryClient.getQueryCache().subscribe(() => {
                updateQueries();
            });
            return unsubscribe;
        }
    }, [queryClient]);

    const handleInvalidateAll = async () => {
        if (!queryClient) return;
        setIsRefreshing(true);
        await queryClient.invalidateQueries();
        setTimeout(() => setIsRefreshing(false), 500); // Visual feedback
    };

    const handleClearAll = () => {
        if (!queryClient) return;
        queryClient.clear();
        updateQueries();
    };

    const handleInvalidate = (queryKeyStr: string) => {
        if (!queryClient) return;
        queryClient.invalidateQueries({ queryKey: JSON.parse(queryKeyStr) });
    };

    const handleRemove = (queryKeyStr: string) => {
        if (!queryClient) return;
        queryClient.removeQueries({ queryKey: JSON.parse(queryKeyStr) });
    };

    const handleRefetch = (queryKeyStr: string) => {
        if (!queryClient) return;
        queryClient.refetchQueries({ queryKey: JSON.parse(queryKeyStr) });
    };

    const toggleExpand = (queryHash: string, data: any) => {
        const next = new Set(expandedIds);
        if (next.has(queryHash)) {
            next.delete(queryHash);
        } else {
            next.add(queryHash);
            setEditData(prev => ({ ...prev, [queryHash]: JSON.stringify(data, null, 2) }));
        }
        setExpandedIds(next);
    };

    const handleSaveCacheData = (queryKeyStr: string, queryHash: string) => {
        if (!queryClient) return;
        try {
            const parsed = JSON.parse(editData[queryHash]);
            queryClient.setQueryData(JSON.parse(queryKeyStr), parsed);
            // Brief flush to show it worked
            setExpandedIds(prev => {
                const next = new Set(prev);
                next.delete(queryHash);
                return next;
            });
        } catch (err) {
            alert('Invalid JSON! Cannot save to cache.');
        }
    };

    const filteredQueries = queries.filter(q => q.queryKey.toLowerCase().includes(searchTerm.toLowerCase()));

    const getStatusColor = (status: string, fetchStatus: string) => {
        if (fetchStatus === 'fetching') return isDark ? 'text-blue-400 bg-blue-500/10' : 'text-blue-600 bg-blue-100';
        if (status === 'error') return isDark ? 'text-red-400 bg-red-500/10' : 'text-red-600 bg-red-100';
        if (status === 'pending') return isDark ? 'text-yellow-400 bg-yellow-500/10' : 'text-yellow-600 bg-yellow-100';
        return isDark ? 'text-green-400 bg-green-500/10' : 'text-green-600 bg-green-100';
    };

    if (!queryClient) {
        return (
            <div className="flex flex-col items-center justify-center h-48 opacity-50 space-y-2">
                <DatabaseZap className="w-8 h-8" />
                <p className="text-sm">QueryClient provider not found in context.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4 relative z-20 h-full flex flex-col">
           <div className="flex justify-between items-center border-b pb-2 shrink-0">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-orange-400 drop-shadow-[0_0_8px_rgba(251,146,60,0.8)]" : "text-orange-600")}>
                    <DatabaseZap className="w-5 h-5 text-orange-500" /> Query Manager
                </h3>
            </div>

            <div className="flex gap-2 shrink-0">
                <button 
                    onClick={handleInvalidateAll}
                    disabled={isRefreshing}
                    className={cn(
                        "flex-1 py-2 flex items-center justify-center gap-2 rounded text-xs font-bold uppercase tracking-widest transition-all",
                        isDark 
                            ? "bg-orange-600 hover:bg-orange-500 text-white shadow-[0_0_15px_rgba(251,146,60,0.3)] disabled:opacity-50" 
                            : "bg-orange-500 hover:bg-orange-600 text-white shadow-md disabled:opacity-50"
                    )}
                >
                    <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
                    Invalidate All Queries
                </button>
                <button 
                    onClick={handleClearAll}
                    className={cn(
                        "px-4 py-2 flex items-center justify-center gap-2 rounded text-xs font-bold uppercase tracking-widest transition-all border",
                        isDark 
                            ? "border-red-500/30 text-red-400 hover:bg-red-500/20" 
                            : "border-red-200 text-red-600 hover:bg-red-50"
                    )}
                    title="Clear entire cache"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
            </div>

            <div className="relative shrink-0 border-b pb-4 border-dashed border-gray-700/50">
                <Search className={cn("absolute left-2.5 top-2.5 w-4 h-4", isDark ? "text-gray-500" : "text-gray-400")} />
                <input
                    type="text"
                    placeholder="Filter query keys..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className={cn(
                        "w-full pl-9 pr-4 py-2 rounded text-xs font-mono outline-none border transition-colors",
                        isDark 
                            ? "bg-black/50 border-gray-800 text-orange-100 focus:border-orange-500/50" 
                            : "bg-white border-slate-300 focus:border-orange-500/50"
                    )}
                />
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pb-4">
                <AnimatePresence>
                    {filteredQueries.map(query => {
                        const isStale = query.dataUpdatedAt > 0 && Date.now() - query.dataUpdatedAt > query.staleTime;
                        return (
                            <motion.div 
                                key={query.queryHash}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className={cn(
                                    "p-3 rounded border text-xs relative overflow-hidden group transition-all",
                                    isDark ? "bg-black/40 border-gray-800 hover:border-orange-500/30" : "bg-white border-slate-200 hover:border-orange-300"
                                )}
                            >
                                <div className="flex justify-between items-start mb-2 group/header">
                                    <div 
                                        className="font-mono font-bold break-all pr-4 cursor-pointer hover:text-orange-500 transition-colors"
                                        onClick={() => toggleExpand(query.queryHash, query.state.data)}
                                    >
                                        {expandedIds.has(query.queryHash) ? '▼' : '▶'} {query.queryKey}
                                    </div>
                                    <div className={cn("px-2 py-0.5 rounded text-[10px] font-bold uppercase shrink-0", getStatusColor(query.status, query.fetchStatus))}>
                                        {query.fetchStatus === 'fetching' ? 'fetching' : query.status}
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-2 text-[10px] mb-3">
                                    <div className={cn("py-1 px-2 rounded", isDark ? "bg-white/5" : "bg-slate-100")}>
                                        <span className="opacity-50 block mb-0.5">Observers</span>
                                        <span className="font-mono">{query.subscribers}</span>
                                    </div>
                                    <div className={cn("py-1 px-2 rounded", isDark ? "bg-white/5" : "bg-slate-100")}>
                                        <span className="opacity-50 block mb-0.5">Freshness</span>
                                        <span className={cn("font-bold", isStale ? "text-yellow-500" : "text-green-500")}>
                                            {isStale ? 'Stale' : 'Fresh'}
                                        </span>
                                    </div>
                                    <div className={cn("py-1 px-2 rounded", isDark ? "bg-white/5" : "bg-slate-100")}>
                                        <span className="opacity-50 block mb-0.5">Updated</span>
                                        <span className="font-mono">
                                            {query.dataUpdatedAt ? new Date(query.dataUpdatedAt).toLocaleTimeString() : 'Never'}
                                        </span>
                                    </div>
                                </div>

                                <div className={cn(
                                    "flex gap-2 pt-2 border-t opacity-0 group-hover:opacity-100 transition-opacity",
                                    isDark ? "border-gray-800" : "border-slate-100"
                                )}>
                                    <button onClick={() => handleRefetch(query.queryKey)} className={cn("flex-1 py-1 rounded transition-colors uppercase font-bold text-[10px]", isDark ? "hover:bg-blue-500/20 text-blue-400" : "hover:bg-blue-100 text-blue-600")}>
                                        Refetch
                                    </button>
                                    <button onClick={() => handleInvalidate(query.queryKey)} className={cn("flex-1 py-1 rounded transition-colors uppercase font-bold text-[10px]", isDark ? "hover:bg-orange-500/20 text-orange-400" : "hover:bg-orange-100 text-orange-600")}>
                                        Invalidate
                                    </button>
                                    <button onClick={() => handleRemove(query.queryKey)} className={cn("flex-1 py-1 rounded transition-colors uppercase font-bold text-[10px]", isDark ? "hover:bg-red-500/20 text-red-400" : "hover:bg-red-100 text-red-600")}>
                                        Remove
                                    </button>
                                </div>

                                {expandedIds.has(query.queryHash) && (
                                    <div className={cn("mt-3 pt-3 border-t", isDark ? "border-gray-800" : "border-slate-200")}>
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-[10px] font-bold uppercase opacity-50">Cache Payload (JSON)</span>
                                            <button 
                                                onClick={() => handleSaveCacheData(query.queryKey, query.queryHash)}
                                                className={cn("text-[10px] font-bold uppercase px-2 py-0.5 rounded", isDark ? "bg-green-500/20 text-green-400 hover:bg-green-500/40" : "bg-green-100 text-green-700 hover:bg-green-200")}
                                            >
                                                Save to Cache
                                            </button>
                                        </div>
                                        <textarea
                                            value={editData[query.queryHash] || ''}
                                            onChange={(e) => setEditData(prev => ({ ...prev, [query.queryHash]: e.target.value }))}
                                            className={cn(
                                                "w-full h-32 p-2 text-[10px] font-mono rounded bg-black/50 border outline-none resize-y",
                                                isDark ? "border-gray-800 focus:border-orange-500/50 text-orange-200" : "bg-slate-50 border-slate-300 focus:border-orange-500/50 text-slate-700"
                                            )}
                                            spellCheck={false}
                                        />
                                    </div>
                                )}
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
                
                {filteredQueries.length === 0 && (
                    <div className="h-24 flex items-center justify-center opacity-30 italic text-xs">
                        No queries found matching filter.
                    </div>
                )}
            </div>
        </div>
    );
}
