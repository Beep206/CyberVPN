import React, { useState } from 'react';
import { Bell, Radio, Send, Terminal, AlertTriangle, CheckCircle, Info, Skull } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';

export function EventsTab({ isDark }: { isDark: boolean }) {
    const [eventName, setEventName] = useState('vpn:status:changed');
    const [eventPayload, setEventPayload] = useState('{\n  "status": "connected",\n  "node": "SG-1"\n}');
    
    const dispatchGlobalEvent = () => {
        if (typeof window === 'undefined') return;
        try {
            const detail = JSON.parse(eventPayload);
            const event = new CustomEvent(eventName, { detail });
            window.dispatchEvent(event);
            
            // Also log to console
            console.log(`%c[DevPanel] Dispatched Event:%c ${eventName}`, 'color: #00ff88; font-weight: bold;', 'color: inherit;', detail);
        } catch (e) {
            alert('Invalid JSON payload');
        }
    };

    const triggerNativeNotification = (title: string, body: string, iconType: string) => {
        if (typeof window !== 'undefined' && 'Notification' in window) {
            if (Notification.permission === 'granted') {
                new Notification(title, { body });
            } else if (Notification.permission !== 'denied') {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        new Notification(title, { body });
                    }
                });
            } else {
                alert(`Native Notification (Permission Denied):\n${title}\n${body}`);
            }
        }
    };

    const spoofToast = (type: 'success' | 'error' | 'warning' | 'info') => {
        const messages = {
            success: { title: 'Operation Successful', body: 'The server node was updated.' },
            error: { title: 'Critical Failure', body: 'Failed to establish secure tunnel.' },
            warning: { title: 'High Latency', body: 'Node US-East is experiencing high load.' },
            info: { title: 'System Update', body: 'New version of CyberVPN is available.' },
        };
        const { title, body } = messages[type];
        
        // 1. Try to trigger a native notification
        triggerNativeNotification(`[${type.toUpperCase()}] ${title}`, body, type);
        
        // 2. Dispatch a CustomEvent for the app to pick up if it implements toasts later
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('dev:toast', {
                detail: { type, title, body }
            }));
            console.log(`%c[DevPanel] Spoofed Toast:%c ${type}`, 'color: #ff00ff; font-weight: bold;', 'color: inherit;', messages[type]);
        }
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" : "text-purple-700")}>
                    <Bell className="w-5 h-5 text-purple-500" /> Event Spoofer
                </h3>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                Dispatch fake global system events and push notifications to test your application's responsiveness to asynchronous triggers.
            </p>

            {/* Native / App Toasts */}
            <div className={cn("p-4 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <h4 className={cn("font-bold flex items-center gap-2 mb-3 text-xs uppercase", isDark ? "text-gray-300" : "text-slate-600")}>
                    <Radio className="w-4 h-4" /> Trigger Mock Toasts
                </h4>
                <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => spoofToast('success')} className={cn("p-2 rounded flex flex-col items-center justify-center gap-1 transition-all border", isDark ? "bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20" : "bg-green-50 border-green-200 text-green-700 hover:bg-green-100")}>
                        <CheckCircle className="w-5 h-5" />
                        <span className="text-[10px] font-bold uppercase">Success</span>
                    </button>
                    <button onClick={() => spoofToast('error')} className={cn("p-2 rounded flex flex-col items-center justify-center gap-1 transition-all border", isDark ? "bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20" : "bg-red-50 border-red-200 text-red-700 hover:bg-red-100")}>
                        <Skull className="w-5 h-5" />
                        <span className="text-[10px] font-bold uppercase">Error</span>
                    </button>
                    <button onClick={() => spoofToast('warning')} className={cn("p-2 rounded flex flex-col items-center justify-center gap-1 transition-all border", isDark ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/20" : "bg-yellow-50 border-yellow-200 text-yellow-700 hover:bg-yellow-100")}>
                        <AlertTriangle className="w-5 h-5" />
                        <span className="text-[10px] font-bold uppercase">Warning</span>
                    </button>
                    <button onClick={() => spoofToast('info')} className={cn("p-2 rounded flex flex-col items-center justify-center gap-1 transition-all border", isDark ? "bg-blue-500/10 border-blue-500/30 text-blue-400 hover:bg-blue-500/20" : "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100")}>
                        <Info className="w-5 h-5" />
                        <span className="text-[10px] font-bold uppercase">Info</span>
                    </button>
                </div>
            </div>

            {/* Global CustomEvent Dispatcher */}
            <div className={cn("p-4 border rounded flex-1 flex flex-col", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <h4 className={cn("font-bold flex items-center gap-2 mb-3 text-xs uppercase", isDark ? "text-gray-300" : "text-slate-600")}>
                    <Terminal className="w-4 h-4" /> Global Event Dispatcher
                </h4>
                
                <div className="space-y-3 flex-1 flex flex-col">
                    <div className="space-y-1">
                        <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Event Name (window.dispatchEvent)</label>
                        <input 
                            type="text" 
                            value={eventName}
                            onChange={e => setEventName(e.target.value)}
                            className={cn("w-full px-2 py-1.5 text-xs font-mono rounded border outline-none", isDark ? "bg-gray-900 border-gray-700 focus:border-purple-500 text-white" : "bg-slate-50 border-slate-300 focus:border-purple-500")}
                        />
                    </div>
                    
                    <div className="space-y-1 flex-1 flex flex-col">
                        <label className={cn("text-[10px] font-bold uppercase", isDark ? "text-gray-500" : "text-slate-500")}>Payload (JSON `detail` object)</label>
                        <textarea 
                            value={eventPayload}
                            onChange={e => setEventPayload(e.target.value)}
                            className={cn("w-full flex-1 px-2 py-1.5 text-[10px] font-mono rounded border outline-none whitespace-pre resize-none", isDark ? "bg-gray-900 border-gray-700 focus:border-purple-500 text-green-400" : "bg-slate-50 border-slate-300 focus:border-purple-500 text-green-700")}
                            spellCheck={false}
                        />
                    </div>

                    <button 
                        onClick={dispatchGlobalEvent}
                        className={cn(
                            "w-full py-2 flex items-center justify-center gap-2 rounded text-xs font-bold uppercase tracking-widest transition-all mt-2",
                            isDark 
                                ? "bg-purple-600 hover:bg-purple-500 text-white shadow-[0_0_15px_rgba(168,85,247,0.4)]" 
                                : "bg-purple-500 hover:bg-purple-600 text-white"
                        )}
                    >
                        <Send className="w-4 h-4" /> Dispatch Event
                    </button>
                </div>
            </div>

        </div>
    );
}
