import React, { useState, useEffect } from 'react';
import { Palette, Copy, CheckCircle2, Eye, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';

const THEME_VARS = [
    { name: '--color-matrix-green', label: 'Matrix Green', defaultVal: '#00ff88' },
    { name: '--color-neon-cyan', label: 'Neon Cyan', defaultVal: '#00ffff' },
    { name: '--color-neon-pink', label: 'Neon Pink', defaultVal: '#ff00ff' },
    { name: '--color-neon-purple', label: 'Neon Purple', defaultVal: '#8a2be2' },
    { name: '--color-neon-yellow', label: 'Neon Yellow', defaultVal: '#ffff00' },
];

export function ThemeTab({ isDark }: { isDark: boolean }) {
    const [colors, setColors] = useState<Record<string, string>>({});
    const [copied, setCopied] = useState(false);
    const [wcagErrors, setWcagErrors] = useState<number | null>(null);

    useEffect(() => {
        // Read initial computed styles or use defaults
        if (typeof window !== 'undefined') {
            const root = document.documentElement;
            const computed = getComputedStyle(root);
            let initialColors: Record<string, string> = {};
            
            // First check if we have saved theme
            const savedTheme = localStorage.getItem('DEV_THEME');
            if (savedTheme) {
                try { initialColors = JSON.parse(savedTheme); } catch { /* ignore */ }
            }

            THEME_VARS.forEach(v => {
                if (!initialColors[v.name]) {
                    const val = computed.getPropertyValue(v.name).trim();
                    // If it's empty, use the hardcoded default from the list
                    initialColors[v.name] = val.startsWith('#') || val.startsWith('rgb') ? val : v.defaultVal;
                }
            });
            setColors(initialColors);
        }
    }, []);

    const handleColorChange = (name: string, value: string) => {
        setColors(prev => {
            const next = { ...prev, [name]: value };
            localStorage.setItem('DEV_THEME', JSON.stringify(next));
            return next;
        });
        document.documentElement.style.setProperty(name, value);
    };

    const handleCopyCss = () => {
        const cssLines = Object.entries(colors)
            .map(([name, val]) => `    ${name}: ${val};`)
            .join('\n');
        
        const cssString = `:root {\n${cssLines}\n}`;
        navigator.clipboard.writeText(cssString).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    const handleReset = () => {
        const resetColors: Record<string, string> = {};
        THEME_VARS.forEach(v => {
            resetColors[v.name] = v.defaultVal;
            document.documentElement.style.removeProperty(v.name);
        });
        setColors(resetColors);
        localStorage.removeItem('DEV_THEME');
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-transparent bg-clip-text bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 drop-shadow-[0_0_8px_rgba(255,0,255,0.8)]" : "text-purple-700")}>
                    <Palette className="w-5 h-5 text-pink-500" /> Theme Tweaker
                </h3>
                <button
                    onClick={handleReset}
                    title="Reset to defaults"
                    className={cn(
                        "p-1.5 rounded transition-all flex items-center gap-1 text-[10px] font-bold uppercase",
                        isDark ? "hover:bg-gray-800 text-gray-400 hover:text-white" : "hover:bg-slate-200 text-slate-500 hover:text-slate-800"
                    )}
                >
                    Reset
                </button>
            </div>

            <div className={cn("p-4 border rounded relative", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-pink-400" : "text-pink-600")}>
                    <Palette className="w-4 h-4" /> Live CSS Variables
                </h4>
                <p className={cn("text-[10px] mb-4", isDark ? "text-gray-500" : "text-slate-500")}>Adjust global cyberpunk theme colors in real-time.</p>

                <div className="space-y-4">
                    {THEME_VARS.map((v) => (
                        <div key={v.name} className="flex items-center justify-between">
                            <div>
                                <div className={cn("text-xs font-bold", isDark ? "text-gray-300" : "text-slate-700")}>{v.label}</div>
                                <code className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-400")}>{v.name}</code>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={cn("font-mono text-xs uppercase w-16 text-right", isDark ? "text-gray-400" : "text-slate-600")}>
                                    {colors[v.name] || v.defaultVal}
                                </span>
                                <div className="relative w-8 h-8 rounded overflow-hidden shadow-inner border border-gray-500/30">
                                    <input
                                        type="color"
                                        value={colors[v.name] || v.defaultVal}
                                        onChange={(e) => handleColorChange(v.name, e.target.value)}
                                        className="absolute -top-2 -left-2 w-12 h-12 cursor-pointer"
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <button
                onClick={handleCopyCss}
                className={cn(
                    "w-full py-3 flex items-center justify-center gap-2 rounded-lg font-bold text-xs uppercase tracking-widest transition-all",
                    isDark 
                        ? "bg-gray-900 border border-purple-500/30 text-purple-400 hover:bg-purple-900/30 hover:border-purple-500/60 shadow-[0_0_15px_rgba(168,85,247,0.15)]" 
                        : "bg-purple-50 border border-purple-200 text-purple-600 hover:bg-purple-100"
                )}
            >
                {copied ? (
                    <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} className="flex items-center gap-2 text-green-500">
                        <CheckCircle2 className="w-4 h-4" /> Copied to Clipboard
                    </motion.div>
                ) : (
                    <>
                        <Copy className="w-4 h-4" /> Copy CSS Variables
                    </>
                )}
            </button>

            <div className={cn("p-4 border rounded", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex justify-between items-center mb-2">
                    <h4 className={cn("font-bold flex items-center gap-2", isDark ? "text-cyan-400" : "text-cyan-600")}>
                        <Eye className="w-4 h-4" /> WCAG Contrast Scan
                    </h4>
                </div>
                <p className={cn("text-[10px] mb-4", isDark ? "text-gray-500" : "text-slate-500")}>Calculates the relative luminance of text against its background. Flags elements failing the AA standard (ratio &lt; 4.5:1).</p>
                
                <button
                    onClick={() => {
                        // Very naive WCAG scanner
                        if (typeof window === 'undefined') return;
                        
                        document.querySelectorAll('.dev-wcag-error').forEach(el => el.classList.remove('dev-wcag-error'));
                        
                        const getLuminance = (r: number, g: number, b: number) => {
                            const a = [r, g, b].map(v => {
                                v /= 255;
                                return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                            });
                            return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
                        };
                        
                        const parseColor = (str: string) => {
                            const m = str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                            return m ? [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])] : null;
                        };
                        
                        let errors = 0;
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, {
                            acceptNode: (node) => {
                                const el = node as HTMLElement;
                                // skip panel, script, style, empty elements
                                if (el.closest('#dev-panel-root') || ['SCRIPT', 'STYLE'].includes(el.tagName) || !el.innerText?.trim()) {
                                    return NodeFilter.FILTER_REJECT;
                                }
                                return NodeFilter.FILTER_ACCEPT;
                            }
                        });

                        const nodes = [];
                        let currentNode;
                        while ((currentNode = walker.nextNode())) nodes.push(currentNode as HTMLElement);

                        nodes.forEach((el) => {
                            const style = window.getComputedStyle(el);
                            if (style.display === 'none' || style.visibility === 'hidden') return;
                            
                            // Naive: Only check elements with distinct background colors (not transparent)
                            if (style.backgroundColor && !style.backgroundColor.includes('rgba(0, 0, 0, 0)')) {
                                const fg = parseColor(style.color);
                                const bg = parseColor(style.backgroundColor);
                                if (fg && bg) {
                                    const l1 = getLuminance(fg[0], fg[1], fg[2]);
                                    const l2 = getLuminance(bg[0], bg[1], bg[2]);
                                    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
                                    
                                    // 4.5:1 is the AA threshold for normal text
                                    if (ratio < 4.5) {
                                        el.classList.add('dev-wcag-error');
                                        el.style.outline = '2px dashed red';
                                        el.style.outlineOffset = '2px';
                                        errors++;
                                    }
                                }
                            }
                        });
                        
                        setWcagErrors(errors);
                        setTimeout(() => {
                            document.querySelectorAll('.dev-wcag-error').forEach(el => {
                                (el as HTMLElement).style.outline = '';
                                (el as HTMLElement).style.outlineOffset = '';
                                el.classList.remove('dev-wcag-error');
                            });
                        }, 5000);
                    }}
                    className={cn(
                        "w-full py-2 text-xs font-bold rounded uppercase tracking-widest transition-colors mb-2 border",
                        wcagErrors && wcagErrors > 0
                            ? (isDark ? "bg-red-500/20 text-red-300 border-red-500 shadow-[0_0_10px_rgba(239,68,68,0.4)]" : "bg-red-100 text-red-700 border-red-500")
                            : (isDark ? "bg-gray-900 border-gray-700 text-gray-400 hover:border-cyan-500/50 hover:text-cyan-400" : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100")
                    )}
                >
                    Run Page Scan
                </button>
                {wcagErrors !== null && (
                    <div className={cn("text-[10px] font-bold mt-2 flex items-center justify-between", wcagErrors === 0 ? "text-green-500" : "text-red-500")}>
                        <span>Scan Complete.</span>
                        <span className="flex items-center gap-1">
                            {wcagErrors > 0 && <ShieldAlert className="w-3 h-3" />} {wcagErrors} Violations Found (Cleared in 5s)
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
}
