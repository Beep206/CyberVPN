export type NetworkLogEntry = {
    id: string;
    url: string;
    method: string;
    status?: number;
    duration?: number;
    timestamp: number;
    reqBody?: any;
    resBody?: any;
    reqHeaders?: Record<string, string>;
    resHeaders?: Record<string, string>;
    isMocked?: boolean;
};

export type MockRule = {
    id: string;
    urlPattern: string;
    active: boolean;
    method: 'ALL' | 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    pattern: string;
    status: number;
    delayMs?: number; // Optional artificial latency per-endpoint
    responsePattern: Record<string, any>;
};

type Listener = (logs: NetworkLogEntry[]) => void;

class NetworkLogger {
    private logs: NetworkLogEntry[] = [];
    private listeners: Set<Listener> = new Set();
    private isIntercepting = false;

    // Chaos Simulator properties
    public chaosLatency = 0;
    public chaosFailureRate = 0;

    // Mock Rules
    public mockRules: MockRule[] = [];

    // Save references to originals
    private originalFetch: typeof window.fetch | null = null;
    private originalXhrOpen: typeof XMLHttpRequest.prototype.open | null = null;
    private originalXhrSend: typeof XMLHttpRequest.prototype.send | null = null;

    subscribe(listener: Listener) {
        this.listeners.add(listener);
        listener(this.logs);
        return () => this.listeners.delete(listener);
    }

    private notify() {
        // Need to pass a new array so React state updates
        const currentLogs = [...this.logs];
        this.listeners.forEach((l) => l(currentLogs));
    }

    addLog(log: NetworkLogEntry) {
        this.logs = [log, ...this.logs].slice(0, 100); // keep last 100
        this.notify();
    }

    updateLog(id: string, updates: Partial<NetworkLogEntry>) {
        this.logs = this.logs.map((L) => (L.id === id ? { ...L, ...updates } : L));
        this.notify();
    }

    clear() {
        this.logs = [];
        this.notify();
    }

    start() {
        if (typeof window === 'undefined' || this.isIntercepting) return;
        this.isIntercepting = true;

        this.originalFetch = window.fetch;
        this.originalXhrOpen = window.XMLHttpRequest.prototype.open;
        this.originalXhrSend = window.XMLHttpRequest.prototype.send;

        this.interceptFetch();
        this.interceptXHR();
    }

    stop() {
        if (!this.isIntercepting) return;
        this.isIntercepting = false;

        if (this.originalFetch) window.fetch = this.originalFetch;
        if (this.originalXhrOpen) window.XMLHttpRequest.prototype.open = this.originalXhrOpen;
        if (this.originalXhrSend) window.XMLHttpRequest.prototype.send = this.originalXhrSend;
    }

    private interceptFetch() {
        const _fetch = this.originalFetch!;
        window.fetch = async (input, init) => {
            const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
            const method = init?.method || (input instanceof Request ? input.method : 'GET');
            const id = Math.random().toString(36).substring(7);
            const startTime = performance.now();

            // Try to parse body safely for UI display
            let parsedReqBody = init?.body;
            if (typeof parsedReqBody === 'string') {
                try { parsedReqBody = JSON.parse(parsedReqBody); } catch { /* ignore */ }
            }

            this.addLog({
                id,
                url,
                method: method.toUpperCase(),
                timestamp: Date.now(),
                reqBody: parsedReqBody,
                reqHeaders: init?.headers as any
            });

            // Check Mocks
            try {
                const activeMock = this.mockRules.find(m =>
                    m.active &&
                    (m.method === 'ALL' || m.method === method.toUpperCase()) &&
                    new RegExp(m.urlPattern).test(url)
                );

                if (activeMock) {
                    const delay = activeMock.delayMs || 0;
                    if (delay > 0) {
                        await new Promise(r => setTimeout(r, delay));
                    }

                    const mockResBody = activeMock.responsePattern;
                    // The original code had `activeMock.responseBody` which was a string.
                    // Now `responsePattern` is `Record<string, any>`, so it's already parsed JSON.
                    // No need for `try { mockResBody = JSON.parse(activeMock.responseBody) } catch { /* text */ }`

                    this.updateLog(id, {
                        status: activeMock.status,
                        duration: delay || Math.round(performance.now() - startTime),
                        resBody: mockResBody,
                        resHeaders: { 'x-mocked-by': 'DevPanel' },
                        isMocked: true
                    });

                    return new Response(JSON.stringify(activeMock.responsePattern), {
                        status: activeMock.status,
                        headers: { 'content-type': 'application/json', 'x-mocked-by': 'DevPanel' }
                    });
                }
            } catch (err) {
                console.error("Mock Regex Error", err);
            }

            // Chaos: Artificial Latency
            if (this.chaosLatency > 0) {
                await new Promise(resolve => setTimeout(resolve, this.chaosLatency));
            }

            // Chaos: Artificial Failure
            if (this.chaosFailureRate > 0 && Math.random() * 100 < this.chaosFailureRate) {
                this.updateLog(id, {
                    status: 500,
                    duration: Math.round(performance.now() - startTime),
                    resBody: 'Chaos Simulator Error: Artificial 500 Internal Server Error'
                });
                return new Response(JSON.stringify({ error: "Chaos Simulator Error" }), {
                    status: 500,
                    statusText: "Internal Server Error",
                    headers: { "Content-Type": "application/json" }
                });
            }

            try {
                const response = await _fetch(input, init);
                // Clone response to read body
                const clone = response.clone();

                let resBody: any;
                const contentType = clone.headers.get('content-type') || '';

                try {
                    if (contentType.includes('application/json')) {
                        resBody = await clone.json();
                    } else if (contentType.includes('text/')) {
                        resBody = await clone.text();
                    } else {
                        resBody = `[Binary/Unsupported: ${contentType}]`;
                    }
                } catch (e) {
                    resBody = '[Failed to parse response]';
                }

                const resHeaders: Record<string, string> = {};
                response.headers.forEach((val, key) => { resHeaders[key] = val; });

                this.updateLog(id, {
                    status: response.status,
                    duration: Math.round(performance.now() - startTime),
                    resBody,
                    resHeaders
                });

                return response;
            } catch (error: any) {
                this.updateLog(id, {
                    status: 0,
                    duration: Math.round(performance.now() - startTime),
                    resBody: error?.message || 'Network Error'
                });
                throw error;
            }
        };
    }

    private interceptXHR() {
        const _open = this.originalXhrOpen!;
        const _send = this.originalXhrSend!;
        const self = this;

        window.XMLHttpRequest.prototype.open = function(method: string, url: string | URL, ...args: any[]) {
            (this as any)._networkLogId = Math.random().toString(36).substring(7);
            (this as any)._networkLogMethod = method;
            (this as any)._networkLogUrl = url.toString();
            (this as any)._networkLogStartTime = performance.now();
            
            return _open.apply(this, [method, url as any, ...args] as any);
        };

        window.XMLHttpRequest.prototype.send = function(body?: Document | XMLHttpRequestBodyInit | null) {
            const id = (this as any)._networkLogId;
            if (id) {
                let parsedReqBody = body;
                if (typeof parsedReqBody === 'string') {
                    try { parsedReqBody = JSON.parse(parsedReqBody); } catch { /* ignore */ }
                }

                self.addLog({
                    id,
                    url: (this as any)._networkLogUrl,
                    method: ((this as any)._networkLogMethod || 'GET').toUpperCase(),
                    timestamp: Date.now(),
                    reqBody: parsedReqBody
                });

                this.addEventListener('loadend', () => {
                    const duration = Math.round(performance.now() - (this as any)._networkLogStartTime);
                    
                    let resBody: any = this.responseText;
                    try { resBody = JSON.parse(this.responseText); } catch { /* ignore */ }

                    self.updateLog(id, {
                        status: this.status,
                        duration,
                        resBody
                    });
                });
            }
            return _send.apply(this, [body]);
        };
    }
}

export const networkLogger = new NetworkLogger();
