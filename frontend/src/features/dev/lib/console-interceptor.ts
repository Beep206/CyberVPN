type LogLevel = 'log' | 'info' | 'warn' | 'error' | 'debug';

export interface ConsoleMessage {
    id: string;
    level: LogLevel;
    timestamp: number;
    args: any[];
    stackTrace?: string;
}

export type ConsoleListener = (msg: ConsoleMessage) => void;

let consoleMessageSequence = 0;

function getConsoleMessageId(): string {
    consoleMessageSequence += 1;
    return `console-${consoleMessageSequence}`;
}

class ConsoleInterceptor {
    private originalConsole: Partial<Console> = {};
    private isIntercepting = false;
    private buffer: ConsoleMessage[] = [];
    private listeners: Set<ConsoleListener> = new Set();
    private capacity = 500; // Store max 500 logs

    constructor() {
        if (typeof window !== 'undefined') {
            this.originalConsole = {
                log: console.log.bind(console),
                info: console.info.bind(console),
                warn: console.warn.bind(console),
                error: console.error.bind(console),
                debug: console.debug.bind(console)
            };
        }
    }

    start() {
        if (typeof window === 'undefined' || this.isIntercepting) return;

        const methods: LogLevel[] = ['log', 'info', 'warn', 'error', 'debug'];
        
        methods.forEach(method => {
            console[method] = (...args: any[]) => {
                // Call original immediately
                if (this.originalConsole[method]) {
                    (this.originalConsole[method] as any)(...args);
                }

                // Never intercept our own dev panel logs to prevent infinite loops
                if (args[0] && typeof args[0] === 'string' && args[0].includes('[Dev Tools]')) return;
                
                // Exclude React/NextJS fast refresh noise if needed
                if (args[0] && typeof args[0] === 'string' && args[0].includes('Fast Refresh')) return;

                const msg: ConsoleMessage = {
                    id: getConsoleMessageId(),
                    level: method,
                    timestamp: Date.now(),
                    args: args.map(arg => this.cloneSafe(arg)), // Clone to prevent mutation later
                    stackTrace: method === 'error' ? new Error().stack : undefined
                };

                this.buffer.unshift(msg); 
                if (this.buffer.length > this.capacity) {
                    this.buffer.pop();
                }

                this.listeners.forEach(l => l(msg));
            };
        });

        this.isIntercepting = true;
        console.log('[Dev Tools] Console Intercepted globally.');
    }

    stop() {
        if (!this.isIntercepting) return;
        
        const methods: LogLevel[] = ['log', 'info', 'warn', 'error', 'debug'];
        methods.forEach(method => {
            if (this.originalConsole[method]) {
                console[method] = this.originalConsole[method] as any;
            }
        });

        this.isIntercepting = false;
    }

    // Attempt to clone args for history, falling back to strings if not cloneable
    private cloneSafe(arg: any): any {
        if (arg === null || arg === undefined) return arg;
        if (typeof arg !== 'object') return arg;
        
        try {
            // Handle Errors specially
            if (arg instanceof Error) {
                return { _isError: true, name: arg.name, message: arg.message, stack: arg.stack };
            }
            // Handle Dates
            if (arg instanceof Date) return arg.toISOString();
            
            // Standard clone
            return JSON.parse(JSON.stringify(arg));
        } catch (e) {
            // Circular dependency or Symbol, just return string
            try {
                return `[Unclonable Object: ${Object.prototype.toString.call(arg)}]`;
            } catch {
                return '[Unclonable Object]';
            }
        }
    }

    subscribe(listener: ConsoleListener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    getHistory() {
        return this.buffer;
    }

    clear() {
        this.buffer = [];
    }
}

export const consoleInterceptor = new ConsoleInterceptor();
