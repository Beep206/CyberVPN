import React, { useState, useEffect } from 'react';
import { Wand2, Keyboard, CheckCircle2, FlaskConical, Save, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'motion/react';

// Generates chaotic valid test data
const fakeData = {
    email: () => `test_${Math.random().toString(36).substring(2, 8)}@cybervpn.local`,
    password: () => `Sup3rSecr3t!${Math.floor(Math.random() * 9999)}`,
    name: () => ['Neon', 'Cipher', 'Vortex', 'Pulse', 'Onyx'][Math.floor(Math.random() * 5)] + ' ' + Math.floor(Math.random() * 100),
    url: () => `https://node-${Math.random().toString(36).substring(2, 6)}.cybervpn.net`,
    ip: () => `${Math.floor(Math.random()*255)}.${Math.floor(Math.random()*255)}.${Math.floor(Math.random()*255)}.${Math.floor(Math.random()*255)}`,
    text: () => 'Mock string ' + Math.random().toString(36).substring(7),
    number: () => Math.floor(Math.random() * 10000).toString(),
};

type FillResult = { filled: number; type: string };

type AutofillPreset = {
    id: string;
    name: string;
    description: string;
    data: Record<string, string>; // Maps input `name` or `type` to a specific string
};

const DEFAULT_PRESETS: AutofillPreset[] = [
    {
        id: 'sql_inject_1',
        name: 'SQL Injection 1',
        description: 'Attempts basic logical OR bypassing',
        data: {
            'email': "admin' OR '1'='1",
            'user': "admin' OR '1'='1",
            'password': "' OR '1'='1"
        }
    },
    {
        id: 'xss_payload_1',
        name: 'Basic XSS',
        description: 'Injects simple alert script wrapper',
        data: {
            'text': "<script>alert('XSS')</script>",
            'name': "<b>Test</b>",
            'default': "<img src=x onerror=alert(1)>"
        }
    }
];

export function AutofillTab({ isDark }: { isDark: boolean }) {
    const [lastAction, setLastAction] = useState<FillResult | null>(null);
    const [presets, setPresets] = useState<AutofillPreset[]>(DEFAULT_PRESETS);
    const [activePresetId, setActivePresetId] = useState<string>('random_chaos');

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('DEV_AUTOFILL_PRESETS');
            if (saved) {
                try {
                    const parsed = JSON.parse(saved);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        setPresets(parsed);
                    }
                } catch { }
            }
        }
    }, []);

    const savePresets = (newPresets: AutofillPreset[]) => {
        setPresets(newPresets);
        if (typeof window !== 'undefined') {
            localStorage.setItem('DEV_AUTOFILL_PRESETS', JSON.stringify(newPresets));
        }
    };

    const triggerFill = (type: 'all' | 'form') => {
        if (typeof document === 'undefined') return;

        let inputs: NodeListOf<HTMLInputElement | HTMLTextAreaElement>;
        
        if (type === 'form') {
            // Find inputs inside the first found <form> excluding the dev panel
            const forms = Array.from(document.querySelectorAll('form')).filter(f => !f.closest('#dev-panel-root'));
            if (forms.length > 0) {
                inputs = forms[0].querySelectorAll('input:not([type="hidden"]), textarea');
            } else {
                inputs = document.querySelectorAll('input:not([type="hidden"]), textarea') as any; // fallback
            }
        } else {
            // All inputs on page excluding dev panel
            const all = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea')) as (HTMLInputElement | HTMLTextAreaElement)[];
            inputs = all.filter(el => !el.closest('#dev-panel-root')) as unknown as NodeListOf<HTMLInputElement>;
        }

        let filledCount = 0;

        const activePreset = presets.find(p => p.id === activePresetId);

        inputs.forEach(input => {
            const name = input.name.toLowerCase();
            const type = input.type.toLowerCase();
            let val = '';

            if (activePresetId === 'random_chaos') {
                if (type === 'email' || name.includes('email')) {
                    val = fakeData.email();
                } else if (type === 'password' || name.includes('pass')) {
                    val = fakeData.password();
                } else if (type === 'url' || name.includes('url') || name.includes('link')) {
                    val = fakeData.url();
                } else if (name.includes('ip') || name.includes('address')) {
                    val = fakeData.ip();
                } else if (name.includes('name') || name.includes('user')) {
                    val = fakeData.name();
                } else if (type === 'number') {
                    val = fakeData.number();
                } else {
                    val = fakeData.text();
                }
            } else if (activePreset) {
                // Exact name match
                if (activePreset.data[name]) {
                    val = activePreset.data[name];
                } 
                // Partial name match
                else if (Object.keys(activePreset.data).some(k => name.includes(k))) {
                    const matchingKey = Object.keys(activePreset.data).find(k => name.includes(k))!;
                    val = activePreset.data[matchingKey];
                }
                // Fallback default
                else if (activePreset.data['default']) {
                    val = activePreset.data['default'];
                } else {
                    return; // Skip filling this input
                }
            }

            // Set value and trigger React events
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (setter) {
                setter.call(input, val);
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                filledCount++;
            }
        });

        setLastAction({ filled: filledCount, type });
        setTimeout(() => setLastAction(null), 3000);
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2 shrink-0">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-pink-400 drop-shadow-[0_0_8px_rgba(244,114,182,0.8)]" : "text-pink-600")}>
                    <Wand2 className="w-5 h-5 text-pink-500" /> Form Autofiller
                </h3>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                The Magic Wand safely traverses the active DOM (outside of the Dev Panel) and injects realistic mock data (Emails, Passwords, URLs, IP Addresses) into empty standard HTML inputs to save typing.
            </p>

            {/* Injection Scenario Selector */}
            <div className={cn("p-4 border rounded flex flex-col gap-3", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-pink-400" : "text-pink-600")}>
                        <FlaskConical className="w-4 h-4" /> Injection Scenario
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>
                        Choose whether to generate random realistic data or apply a specific vulnerability payload to test form validation logic.
                    </p>
                </div>
                
                <select
                    value={activePresetId}
                    onChange={(e) => setActivePresetId(e.target.value)}
                    className={cn(
                        "w-full px-3 py-2 text-xs font-mono rounded border outline-none transition-colors",
                        isDark ? "bg-gray-900 border-gray-700 text-pink-200 focus:border-pink-500" : "bg-slate-50 border-slate-300 focus:border-pink-500"
                    )}
                >
                    <option value="random_chaos">Random Realistic Data (Default)</option>
                    <optgroup label="Custom Vulnerability Payloads">
                        {presets.map(p => (
                            <option key={p.id} value={p.id}>{p.name} - {p.description}</option>
                        ))}
                    </optgroup>
                </select>

                {activePresetId !== 'random_chaos' && (
                    <div className={cn("p-2 rounded text-[10px] font-mono border", isDark ? "bg-gray-900 border-gray-800 text-gray-400" : "bg-slate-100 border-slate-200 text-slate-600")}>
                        <div className="font-bold mb-1 opacity-70">Payload Map:</div>
                        <pre className="whitespace-pre-wrap">
                            {JSON.stringify(presets.find(p => p.id === activePresetId)?.data || {}, null, 2)}
                        </pre>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-2 gap-4">
                <button 
                    onClick={() => triggerFill('form')}
                    className={cn(
                        "p-4 flex flex-col items-center justify-center gap-3 rounded-lg border-2 transition-all group",
                        isDark 
                            ? "bg-black/50 border-pink-500/30 hover:bg-pink-500/10 hover:border-pink-500 hover:shadow-[0_0_15px_rgba(244,114,182,0.3)] text-gray-300 hover:text-pink-400" 
                            : "bg-white border-pink-200 hover:bg-pink-50 hover:border-pink-400 hover:shadow-md text-slate-600 hover:text-pink-600"
                    )}
                >
                    <Keyboard className="w-8 h-8 opacity-70 group-hover:opacity-100 transition-opacity" />
                    <div className="text-center">
                        <div className="font-bold text-xs uppercase mb-1">Fill Active Form</div>
                        <div className="text-[9px] opacity-60">Targets first &lt;form&gt; tag</div>
                    </div>
                </button>

                <button 
                    onClick={() => triggerFill('all')}
                    className={cn(
                        "p-4 flex flex-col items-center justify-center gap-3 rounded-lg border-2 transition-all group",
                        isDark 
                            ? "bg-black/50 border-purple-500/30 hover:bg-purple-500/10 hover:border-purple-500 hover:shadow-[0_0_15px_rgba(168,85,247,0.3)] text-gray-300 hover:text-purple-400" 
                            : "bg-white border-purple-200 hover:bg-purple-50 hover:border-purple-400 hover:shadow-md text-slate-600 hover:text-purple-600"
                    )}
                >
                    <Wand2 className="w-8 h-8 opacity-70 group-hover:opacity-100 transition-opacity" />
                    <div className="text-center">
                        <div className="font-bold text-xs uppercase mb-1">Nuke All Inputs</div>
                        <div className="text-[9px] opacity-60">Scans entire page layout</div>
                    </div>
                </button>
            </div>

            <AnimatePresence>
                {lastAction && (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className={cn(
                            "flex items-center justify-center gap-2 p-3 rounded-md text-xs font-bold border",
                            isDark ? "bg-green-500/20 text-green-400 border-green-500/30" : "bg-green-100 text-green-700 border-green-200"
                        )}
                    >
                        <CheckCircle2 className="w-4 h-4" />
                        Successfully injected {lastAction.filled} inputs
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
