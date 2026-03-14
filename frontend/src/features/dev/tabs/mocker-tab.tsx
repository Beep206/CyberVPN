import React, { useState, useEffect } from 'react';
import { Unplug, Plus, Trash2, Edit2, Play, Square, Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'motion/react';
import { networkLogger, type MockRule } from '../lib/network-logger';

export function MockerTab({ isDark }: { isDark: boolean }) {
    const [rules, setRules] = useState<MockRule[]>([]);
    const [editingId, setEditingId] = useState<string | null>(null);

    // Initial state setup to read from logger and localStorage
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('DEV_MOCK_RULES');
            let initial: MockRule[] = [];
            if (saved) {
                try { initial = JSON.parse(saved); } catch { /* err */ }
            }
            // Apply to logger instantly
            networkLogger.mockRules = initial;
            setRules(initial);
        }
    }, []);

    const saveRules = (newRules: MockRule[]) => {
        setRules(newRules);
        networkLogger.mockRules = newRules;
        if (typeof window !== 'undefined') {
            localStorage.setItem('DEV_MOCK_RULES', JSON.stringify(newRules));
        }
    };

    const addRule = () => {
        const newRule: MockRule = {
            id: Math.random().toString(36).substring(7),
            urlPattern: '/api/example',
            active: true,
            method: 'ALL',
            status: 200,
            delay: 500,
            responseBody: '{\n  "status": "success",\n  "data": []\n}'
        };
        const next = [newRule, ...rules];
        saveRules(next);
        setEditingId(newRule.id);
    };

    const deleteRule = (id: string) => {
        const next = rules.filter(r => r.id !== id);
        saveRules(next);
        if (editingId === id) setEditingId(null);
    };

    const toggleRuleActive = (id: string, active: boolean) => {
        const next = rules.map(r => r.id === id ? { ...r, active } : r);
        saveRules(next);
    };

    const updateRule = (id: string, updates: Partial<MockRule>) => {
        const next = rules.map(r => r.id === id ? { ...r, ...updates } : r);
        saveRules(next);
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-neon-cyan drop-shadow-[0_0_8px_rgba(0,255,255,0.8)]" : "text-emerald-700")}>
                    <Unplug className="w-5 h-5" /> API Response Mocker
                </h3>
                <button
                    onClick={addRule}
                    className={cn(
                        "px-3 py-1.5 rounded transition-all flex items-center gap-1 text-[10px] font-bold uppercase",
                        isDark ? "bg-neon-cyan/20 text-neon-cyan hover:bg-neon-cyan/40 border border-neon-cyan/30" : "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                    )}
                >
                    <Plus className="w-3.5 h-3.5" /> Add Mock
                </button>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                Intercept outgoing `fetch` requests matching Regex patterns and return custom JSON responses. Ideal for testing UI empty states, errors, and mock data.
            </p>

            <div className="flex-1 overflow-auto space-y-4 pr-1">
                <AnimatePresence>
                    {rules.length === 0 && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={cn("p-8 text-center italic text-xs border rounded border-dashed", isDark ? "border-gray-800 text-gray-500" : "border-slate-300 text-slate-400")}>
                            No active mocks. Click "Add Mock" to begin intercepting.
                        </motion.div>
                    )}
                    {rules.map(rule => (
                        <motion.div 
                            key={rule.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className={cn(
                                "border rounded overflow-hidden transition-colors",
                                isDark ? "border-gray-800 bg-black/50" : "border-slate-200 bg-white"
                            )}
                        >
                            {/* Rule Header */}
                            <div className={cn("p-3 flex items-center gap-3", isDark ? "bg-gray-900 border-b border-gray-800" : "bg-slate-50 border-b border-slate-200")}>
                                <button
                                    onClick={() => toggleRuleActive(rule.id, !rule.active)}
                                    className={cn(
                                        "p-1.5 rounded transition-colors",
                                        rule.active
                                            ? (isDark ? "bg-emerald-500/20 text-emerald-400" : "bg-emerald-100 text-emerald-600")
                                            : (isDark ? "bg-gray-800 text-gray-500" : "bg-slate-200 text-slate-400")
                                    )}
                                    title={rule.active ? "Enabled" : "Disabled"}
                                >
                                    {rule.active ? <Play className="w-4 h-4 fill-current" /> : <Square className="w-4 h-4" />}
                                </button>
                                
                                <div className="flex-1 truncate flex items-center gap-2">
                                    <span className={cn(
                                        "px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider",
                                        rule.method === 'ALL' ? (isDark ? "bg-gray-800 text-gray-300" : "bg-slate-200 text-slate-600")
                                        : rule.method === 'GET' ? (isDark ? "bg-blue-500/20 text-blue-400" : "bg-blue-100 text-blue-600")
                                        : rule.method === 'POST' ? (isDark ? "bg-green-500/20 text-green-400" : "bg-green-100 text-green-600")
                                        : rule.method === 'DELETE' ? (isDark ? "bg-red-500/20 text-red-400" : "bg-red-100 text-red-600")
                                        : (isDark ? "bg-yellow-500/20 text-yellow-400" : "bg-yellow-100 text-yellow-600")
                                    )}>
                                        {rule.method}
                                    </span>
                                    <span className={cn("font-mono text-xs truncate", !rule.active && "opacity-50 line-through")}>
                                        {rule.urlPattern}
                                    </span>
                                    <span className={cn(
                                        "ml-auto text-[10px] font-bold px-2 py-0.5 rounded",
                                        rule.status >= 200 && rule.status < 300 ? "text-green-500 bg-green-500/10"
                                        : rule.status >= 400 ? "text-red-500 bg-red-500/10"
                                        : "text-blue-500 bg-blue-500/10"
                                    )}>
                                        HTTP {rule.status}
                                    </span>
                                </div>

                                <button
                                    onClick={() => setEditingId(editingId === rule.id ? null : rule.id)}
                                    className={cn("p-1.5 rounded transition-colors", isDark ? "hover:bg-gray-800 text-gray-400 hover:text-white" : "hover:bg-slate-200 text-slate-500 hover:text-slate-800")}
                                >
                                    {editingId === rule.id ? <Check className="w-4 h-4 text-green-500" /> : <Edit2 className="w-4 h-4" />}
                                </button>
                                <button
                                    onClick={() => deleteRule(rule.id)}
                                    className={cn("p-1.5 rounded transition-colors", isDark ? "hover:bg-red-500/20 text-gray-500 hover:text-red-400" : "hover:bg-red-100 text-slate-400 hover:text-red-500")}
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>

                            {/* Rule Editor */}
                            <AnimatePresence>
                                {editingId === rule.id && (
                                    <motion.div 
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="overflow-hidden border-t border-gray-800/50"
                                    >
                                        <div className="p-4 space-y-4">
                                            <div className="grid grid-cols-2 gap-4">
                                                <div className="space-y-1">
                                                    <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>URL Regex/Substring</label>
                                                    <input 
                                                        type="text" 
                                                        value={rule.urlPattern} 
                                                        onChange={e => updateRule(rule.id, { urlPattern: e.target.value })}
                                                        className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700 focus:border-neon-cyan" : "bg-white border-slate-300 focus:border-blue-500")}
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Method</label>
                                                    <select
                                                        value={rule.method}
                                                        onChange={e => updateRule(rule.id, { method: e.target.value as any })}
                                                        className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700" : "bg-white border-slate-300")}
                                                    >
                                                        <option value="ALL">ALL</option>
                                                        <option value="GET">GET</option>
                                                        <option value="POST">POST</option>
                                                        <option value="PUT">PUT</option>
                                                        <option value="DELETE">DELETE</option>
                                                        <option value="PATCH">PATCH</option>
                                                    </select>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-2 gap-4">
                                                <div className="space-y-1">
                                                    <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Status Code</label>
                                                    <input 
                                                        type="number" 
                                                        value={rule.status} 
                                                        onChange={e => updateRule(rule.id, { status: parseInt(e.target.value) || 200 })}
                                                        className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700" : "bg-white border-slate-300")}
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Delay (ms)</label>
                                                    <input 
                                                        type="number" 
                                                        value={rule.delay} 
                                                        onChange={e => updateRule(rule.id, { delay: parseInt(e.target.value) || 0 })}
                                                        className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-black border-gray-700" : "bg-white border-slate-300")}
                                                    />
                                                </div>
                                            </div>

                                            <div className="space-y-1">
                                                <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Response Body (JSON)</label>
                                                <textarea 
                                                    value={rule.responseBody}
                                                    onChange={e => updateRule(rule.id, { responseBody: e.target.value })}
                                                    rows={8}
                                                    className={cn("w-full px-2 py-1.5 text-[10px] font-mono rounded border outline-none whitespace-pre", isDark ? "bg-black border-gray-700 focus:border-neon-cyan" : "bg-white border-slate-300 focus:border-blue-500")}
                                                    spellCheck={false}
                                                />
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
            
        </div>
    );
}
