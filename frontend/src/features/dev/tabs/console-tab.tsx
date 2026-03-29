import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Trash2, Pause, Play, ChevronRight, ChevronDown, Cpu, FastForward } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'motion/react';
import { consoleInterceptor, ConsoleMessage } from '../lib/console-interceptor';

const LogLevelColors = {
    log: 'text-gray-300',
    info: 'text-sky-400',
    warn: 'text-yellow-400',
    error: 'text-red-400',
    debug: 'text-purple-400'
};

const LogLevelBg = {
    log: 'bg-transparent',
    info: 'bg-sky-500/10',
    warn: 'bg-yellow-500/10',
    error: 'bg-red-500/10 border-red-500/20',
    debug: 'bg-transparent'
};

const SAFE_REPL_CONTEXT: Record<string, () => unknown> = {
    document: () => document,
    history: () => history,
    location: () => location,
    navigator: () => navigator,
    window: () => window,
};

function resolveReadOnlyExpression(expression: string): unknown {
    const trimmed = expression.trim();

    if (!/^[A-Za-z_$][\w$]*(\.[A-Za-z_$][\w$]*)*$/.test(trimmed)) {
        throw new Error('Only read-only dotted paths are allowed, e.g. document.title');
    }

    const [rootKey, ...segments] = trimmed.split('.');
    const rootFactory = SAFE_REPL_CONTEXT[rootKey];

    if (!rootFactory) {
        throw new Error(`Unsupported root object: ${rootKey}`);
    }

    return segments.reduce<unknown>((current, segment) => {
        if (current == null || (typeof current !== 'object' && typeof current !== 'function')) {
            throw new Error(`Cannot read property ${segment}`);
        }

        return Reflect.get(current, segment);
    }, rootFactory());
}

function JsonViewer({ data, name = "" }: { data: any, name?: string }) {
    const [isExpanded, setIsExpanded] = useState(false);

    if (data === null) return <span className="text-gray-500">null</span>;
    if (data === undefined) return <span className="text-gray-500">undefined</span>;
    if (typeof data === 'string') return <span className="text-green-400">"{data}"</span>;
    if (typeof data === 'number') return <span className="text-orange-400">{data}</span>;
    if (typeof data === 'boolean') return <span className="text-blue-400">{data ? 'true' : 'false'}</span>;

    // Handle intercepted errors from cloneSafe
    if (typeof data === 'object' && data._isError) {
        return (
            <div className="text-red-400 font-mono text-xs">
                <div className="font-bold">{data.name}: {data.message}</div>
                <div className="pl-4 whitespace-pre-wrap opacity-70 mt-1">{data.stack}</div>
            </div>
        );
    }

    if (Array.isArray(data)) {
        if (data.length === 0) return <span className="text-gray-400">[]</span>;
        return (
            <div className="inline-block relative">
                <button onClick={() => setIsExpanded(!isExpanded)} className="text-gray-400 hover:text-white flex items-center gap-1 transition-colors">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    <span>Array({data.length})</span>
                </button>
                {isExpanded && (
                    <div className="pl-4 border-l border-gray-700/50 mt-1 space-y-1">
                        {data.map((item, i) => (
                            <div key={i} className="flex gap-2">
                                <span className="text-gray-500 select-none">{i}:</span>
                                <JsonViewer data={item} />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    if (typeof data === 'object') {
        const keys = Object.keys(data);
        if (keys.length === 0) return <span className="text-gray-400">{'{}'}</span>;
        
        return (
            <div className="inline-block relative">
                <button onClick={() => setIsExpanded(!isExpanded)} className="text-gray-400 hover:text-white flex items-center gap-1 transition-colors">
                    {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    <span>{name || 'Object'}</span>
                </button>
                {isExpanded && (
                    <div className="pl-4 border-l border-gray-700/50 mt-1 space-y-1">
                        {keys.map(key => (
                            <div key={key} className="flex gap-2">
                                <span className="text-sky-300">{key}:</span>
                                <JsonViewer data={data[key]} />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    return <span>{String(data)}</span>;
}

export function ConsoleTab({ isDark }: { isDark: boolean }) {
    const [messages, setMessages] = useState<ConsoleMessage[]>([]);
    const [isPaused, setIsPaused] = useState(false);
    const [filter, setFilter] = useState<string>('all');
    const [regexFilter, setRegexFilter] = useState<string>('');
    const [replInput, setReplInput] = useState<string>('');
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Load initial history
        setMessages([...consoleInterceptor.getHistory()]);

        const unsubscribe = consoleInterceptor.subscribe((msg) => {
            if (!isPaused) {
                setMessages(prev => [msg, ...prev].slice(0, 500));
            }
        });

        return () => {
            unsubscribe();
        };
    }, [isPaused]);

    const handleClear = () => {
        consoleInterceptor.clear();
        setMessages([]);
    };

    const runTestLogs = () => {
        console.log("Standard log message generated at", new Date().toLocaleTimeString());
        console.info("User configuration loaded successfully:", { theme: 'dark', language: 'en', premium: true });
        console.warn("API Request delayed by 500ms");
        console.error(new Error("Failed to authenticate user: Token expired"));
        console.table([{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }]);
    };

    const handleEval = (e: React.FormEvent) => {
        e.preventDefault();
        if (!replInput.trim()) return;

        console.log(`> ${replInput}`);
        try {
            const result = resolveReadOnlyExpression(replInput);
            
            // Handle promises heuristically
            if (result instanceof Promise) {
                console.info("Promise { <pending> }");
                result.then(v => console.log("Promise resolved:", v)).catch(err => console.error("Promise rejected:", err));
            } else {
                console.info(result);
            }
        } catch (err: any) {
            console.error(err);
        }
        setReplInput('');
    };

    const filteredMessages = messages.filter(msg => {
        if (filter !== 'all' && msg.level !== filter) return false;
        
        if (regexFilter) {
            try {
                const re = new RegExp(regexFilter, 'i');
                // Basic stringification check for the filter
                const strContent = msg.args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ');
                if (!re.test(strContent)) return false;
            } catch {
                return true; // invalid regex fails open
            }
        }
        return true;
    });

    return (
        <div className="absolute inset-0 flex flex-col relative z-20">
             <div className="flex justify-between items-center border-b pb-2 px-4 shrink-0">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2 mt-4", isDark ? "text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.8)]" : "text-green-600")}>
                    <Terminal className="w-5 h-5 text-green-500" /> Console
                </h3>

                <div className="flex items-center gap-2 mt-4">
                    <button 
                        onClick={runTestLogs}
                        className={cn("px-2 py-1 text-[10px] font-bold uppercase rounded border transition-colors", isDark ? "border-gray-700 text-gray-400 hover:text-white" : "border-slate-300 text-slate-500")}
                    >
                        Test
                    </button>
                    <button 
                        onClick={() => setIsPaused(!isPaused)}
                        className={cn("p-1.5 rounded transition-colors", isPaused ? "bg-yellow-500/20 text-yellow-500" : (isDark ? "hover:bg-gray-800 text-gray-400" : "hover:bg-slate-200 text-slate-500"))}
                        title={isPaused ? "Resume" : "Pause"}
                    >
                        {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                    </button>
                    <button 
                        onClick={handleClear}
                        className={cn("p-1.5 rounded transition-colors", isDark ? "hover:bg-red-500/20 text-red-400" : "hover:bg-red-100 text-red-500")}
                        title="Clear console"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Filter Bar */}
            <div className={cn("px-4 py-2 flex items-center gap-2 border-b shrink-0 text-xs", isDark ? "border-gray-800 bg-black/40" : "border-slate-200 bg-slate-50")}>
                {['all', 'error', 'warn', 'info', 'log'].map(level => (
                    <button
                        key={level}
                        onClick={() => setFilter(level)}
                        className={cn(
                            "px-2 py-1 rounded font-bold uppercase tracking-wider transition-colors",
                            filter === level 
                                ? (isDark ? "bg-gray-800 text-white" : "bg-slate-200 text-slate-800")
                                : (isDark ? "text-gray-500 hover:text-gray-300" : "text-slate-500 hover:text-slate-700")
                        )}
                    >
                        {level}
                    </button>
                ))}

                <div className="mx-2 w-px h-4 bg-gray-700/50" />
                
                <input
                    type="text"
                    placeholder="Regex Filter..."
                    value={regexFilter}
                    onChange={e => setRegexFilter(e.target.value)}
                    className={cn(
                        "px-2 py-1 flex-1 min-w-[100px] text-[10px] font-mono rounded bg-transparent border outline-none",
                        isDark ? "border-gray-800 focus:border-green-500/50 text-gray-300" : "border-slate-300 focus:border-green-500/50 text-slate-700"
                    )}
                />
                
                <span className={cn("ml-auto text-[10px] font-mono", isDark ? "text-gray-600" : "text-slate-400")}>
                    {messages.length} logs
                </span>
            </div>

            {/* Terminal Output */}
            <div 
                ref={scrollRef}
                className={cn(
                    "flex-1 overflow-y-auto font-mono text-xs p-2 flex flex-col-reverse", 
                    isDark ? "bg-[#0c0c0c] text-gray-300" : "bg-white text-slate-700"
                )}
            >
                <div>
                   <AnimatePresence initial={false}>
                        {filteredMessages.map((msg) => (
                            <motion.div 
                                key={msg.id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className={cn(
                                    "p-2 border-b leading-relaxed flex gap-3 break-all relative group",
                                    isDark ? "border-gray-800/50 hover:bg-white/[0.02]" : "border-slate-100 hover:bg-slate-50",
                                    LogLevelBg[msg.level as keyof typeof LogLevelBg],
                                    msg.level === 'error' && "border-l-2 border-l-red-500" 
                                )}
                            >
                                <div className={cn("shrink-0 text-[10px] opacity-40 mt-0.5", isDark ? "text-gray-500" : "text-slate-400")}>
                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 })}
                                </div>
                                <div className={cn("shrink-0 font-bold uppercase w-10 text-[10px] mt-0.5", LogLevelColors[msg.level as keyof typeof LogLevelColors])}>
                                    {msg.level}
                                </div>
                                <div className="flex-1 space-y-1 overflow-hidden">
                                    {msg.args.map((arg, i) => (
                                        <div key={i} className="max-w-full">
                                            {typeof arg === 'string' ? (
                                                <span className={cn(
                                                    msg.level === 'error' && "text-red-400",
                                                    msg.level === 'warn' && "text-yellow-400"
                                                )}>{arg}</span>
                                            ) : (
                                                <JsonViewer data={arg} />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>

                    {messages.length === 0 && (
                        <div className="h-full flex items-center justify-center opacity-30 italic py-10">
                            No logs captured yet...
                        </div>
                    )}
                </div>
            </div>

            {/* REPL Input */}
            <form onSubmit={handleEval} className={cn("p-2 border-t flex items-center gap-2 shrink-0", isDark ? "border-gray-800 bg-gray-900" : "border-slate-200 bg-slate-50")}>
                <FastForward className={cn("w-4 h-4 shrink-0", isDark ? "text-green-500" : "text-green-600")} />
                <input
                    type="text"
                    value={replInput}
                    onChange={(e) => setReplInput(e.target.value)}
                    placeholder="Evaluate JavaScript context... e.g., document.title"
                    className={cn(
                        "w-full bg-transparent border-none outline-none font-mono text-xs",
                        isDark ? "text-gray-200 placeholder:text-gray-600" : "text-slate-800 placeholder:text-slate-400"
                    )}
                    spellCheck={false}
                    autoComplete="off"
                    aria-label="Console read-only inspector"
                />
            </form>
        </div>
    );
}
