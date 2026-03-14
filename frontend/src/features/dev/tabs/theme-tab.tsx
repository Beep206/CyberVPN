import React, { useState, useEffect } from 'react';
import { Palette, Copy, CheckCircle2 } from 'lucide-react';
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

    useEffect(() => {
        // Read initial computed styles or use defaults
        if (typeof window !== 'undefined') {
            const root = document.documentElement;
            const computed = getComputedStyle(root);
            const initialColors: Record<string, string> = {};
            
            THEME_VARS.forEach(v => {
                const val = computed.getPropertyValue(v.name).trim();
                // If it's empty, use the hardcoded default from the list
                initialColors[v.name] = val.startsWith('#') || val.startsWith('rgb') ? val : v.defaultVal;
            });
            setColors(initialColors);
        }
    }, []);

    const handleColorChange = (name: string, value: string) => {
        setColors(prev => ({ ...prev, [name]: value }));
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
        </div>
    );
}
