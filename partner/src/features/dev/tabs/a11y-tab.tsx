import React, { useState, useEffect } from 'react';
import { ScanEye, AlertTriangle, ShieldAlert, MonitorOff, Palette, Route } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'motion/react';

type A11yViolation = {
    id: string;
    element: HTMLElement;
    type: 'missing_alt' | 'missing_aria' | 'div_button' | 'contrast';
    message: string;
    snippet: string;
};

export function A11yTab({ isDark }: { isDark: boolean }) {
    const [violations, setViolations] = useState<A11yViolation[]>([]);
    const [overlayActive, setOverlayActive] = useState(false);
    const [colorMode, setColorMode] = useState<string>('none');
    const [focusOrderActive, setFocusOrderActive] = useState(false);

    // Load saved color mode on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('DEV_A11Y_COLOR_MODE');
            if (saved) {
                setColorMode(saved);
                applyColorFilter(saved);
            }
        }
    }, []);

    const applyColorFilter = (mode: string) => {
        if (typeof window === 'undefined') return;
        
        // Remove existing filter SVG if any
        const existing = document.getElementById('dev-a11y-color-filter');
        if (existing) existing.remove();

        // Reset
        document.body.style.filter = '';
        
        if (mode === 'none') {
            setColorMode('none');
            localStorage.removeItem('DEV_A11Y_COLOR_MODE');
            return;
        }

        // Inject SVG Filters
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.id = 'dev-a11y-color-filter';
        svg.style.display = 'none';
        
        let filterMatrix = '';
        if (mode === 'protanopia') {
            filterMatrix = '0.567, 0.433, 0, 0, 0, 0.558, 0.442, 0, 0, 0, 0, 0.242, 0.758, 0, 0, 0, 0, 0, 1, 0';
        } else if (mode === 'deuteranopia') {
            filterMatrix = '0.625, 0.375, 0, 0, 0, 0.7, 0.3, 0, 0, 0, 0, 0.3, 0.7, 0, 0, 0, 0, 0, 1, 0';
        } else if (mode === 'tritanopia') {
            filterMatrix = '0.95, 0.05, 0, 0, 0, 0, 0.433, 0.567, 0, 0, 0, 0.475, 0.525, 0, 0, 0, 0, 0, 1, 0';
        } else if (mode === 'achromatopsia') {
            filterMatrix = '0.299, 0.587, 0.114, 0, 0, 0.299, 0.587, 0.114, 0, 0, 0.299, 0.587, 0.114, 0, 0, 0, 0, 0, 1, 0';
        }

        const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
        filter.setAttribute('id', 'a11y-color-blindness');

        const colorMatrix = document.createElementNS('http://www.w3.org/2000/svg', 'feColorMatrix');
        colorMatrix.setAttribute('type', 'matrix');
        colorMatrix.setAttribute('values', filterMatrix);

        filter.appendChild(colorMatrix);
        svg.appendChild(filter);
        document.body.appendChild(svg);
        
        // Apply to body
        document.body.style.filter = 'url(#a11y-color-blindness)';
        setColorMode(mode);
        localStorage.setItem('DEV_A11Y_COLOR_MODE', mode);
    };

    const scanDOM = () => {
        if (typeof window === 'undefined') return;
        const newViolations: A11yViolation[] = [];

        // 1. Missing alt text on images
        const images = document.querySelectorAll('img');
        images.forEach((img, i) => {
            if (!img.hasAttribute('alt')) {
                newViolations.push({
                    id: `img-${i}`,
                    element: img,
                    type: 'missing_alt',
                    message: 'Image is missing "alt" attribute',
                    snippet: img.outerHTML.substring(0, 100)
                });
            }
        });

        // 2. Div/Span functioning as buttons without keyboard support or ARIA
        const clickables = document.querySelectorAll('div[onClick], span[onClick]');
        clickables.forEach((el, i) => {
            const isButton = (el as HTMLElement).getAttribute('role') === 'button';
            const hasTabindex = (el as HTMLElement).hasAttribute('tabindex');
            if (!isButton || !hasTabindex) {
                newViolations.push({
                    id: `click-${i}`,
                    element: el as HTMLElement,
                    type: 'div_button',
                    message: 'Non-semantic element has onClick. Needs role="button" and tabindex="0"',
                    snippet: el.outerHTML.substring(0, 100)
                });
            }
        });

        // 3. Form inputs missing labels or aria-labels
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach((input, i) => {
            const hasId = input.hasAttribute('id');
            const hasLabel = hasId && document.querySelector(`label[for="${input.id}"]`);
            const hasAriaLabel = input.hasAttribute('aria-label') || input.hasAttribute('aria-labelledby');
            if (!hasLabel && !hasAriaLabel) {
                 newViolations.push({
                    id: `input-${i}`,
                    element: input as HTMLElement,
                    type: 'missing_aria',
                    message: 'Form input missing associated <label> or aria-label',
                    snippet: input.outerHTML.substring(0, 100)
                });
            }
        });

        // 4. Buttons missing text
        const buttons = document.querySelectorAll('button');
        buttons.forEach((btn, i) => {
            const textContent = btn.textContent?.trim() || '';
            const hasAriaLabel = btn.hasAttribute('aria-label');
            if (textContent === '' && !hasAriaLabel) {
                newViolations.push({
                    id: `btn-${i}`,
                    element: btn as HTMLElement,
                    type: 'missing_aria',
                    message: 'Button has no readable text and is missing aria-label (e.g., Icon buttons)',
                    snippet: btn.outerHTML.substring(0, 100)
                });
            }
        });

        setViolations(newViolations);
    };

    const toggleOverlay = () => {
        const next = !overlayActive;
        setOverlayActive(next);
        
        if (next) {
            scanDOM();
        } else {
            // Remove overlays
            document.querySelectorAll('.dev-a11y-overlay').forEach(el => el.remove());
        }
    };

    // Redraw overlays
    useEffect(() => {
        if (!overlayActive) return;
        document.querySelectorAll('.dev-a11y-overlay').forEach(el => el.remove());
        
        violations.forEach(v => {
            const rect = v.element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return;

            const overlay = document.createElement('div');
            overlay.className = 'dev-a11y-overlay absolute border-2 border-red-500 border-dashed bg-red-500/20 z-[99999] pointer-events-none flex items-start justify-end px-1';
            overlay.style.top = `${rect.top + window.scrollY}px`;
            overlay.style.left = `${rect.left + window.scrollX}px`;
            overlay.style.width = `${rect.width}px`;
            overlay.style.height = `${rect.height}px`;
            
            const badge = document.createElement('span');
            badge.textContent = '!';
            badge.className = 'bg-red-500 text-white text-[10px] font-black w-4 h-4 flex items-center justify-center rounded-full -mx-2 -mt-2 shadow-lg';
            overlay.appendChild(badge);

            document.body.appendChild(overlay);
        });
    }, [violations, overlayActive]);

    const scrollToElem = (elem: HTMLElement) => {
        elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        elem.animate([
            { outline: '4px solid transparent' },
            { outline: '4px solid red' },
            { outline: '4px solid transparent' }
        ], { duration: 1500 });
    };

    const toggleFocusOrder = () => {
        const next = !focusOrderActive;
        setFocusOrderActive(next);
        
        const existing = document.getElementById('dev-a11y-focus-order');
        if (existing) existing.remove();

        if (next) {
            // Find all tabbable elements
            const focusable = Array.from(document.querySelectorAll<HTMLElement>('a[href], button, input, textarea, select, details, [tabindex]:not([tabindex="-1"])'))
                .filter(el => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden') && el.offsetParent !== null);
            
            if (focusable.length === 0) return;

            // Sort by tabindex (basic approximation, real DOM tabindex sorting is complex)
            focusable.sort((a, b) => {
                const ta = a.tabIndex;
                const tb = b.tabIndex;
                if (ta > 0 && tb === 0) return -1;
                if (ta === 0 && tb > 0) return 1;
                return ta - tb;
            });

            // Draw SVG
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.id = 'dev-a11y-focus-order';
            svg.style.position = 'absolute';
            svg.style.top = '0';
            svg.style.left = '0';
            svg.style.width = '100%';
            svg.style.height = `${document.documentElement.scrollHeight}px`;
            svg.style.pointerEvents = 'none';
            svg.style.zIndex = '99998';

            const points: string[] = [];
            
            focusable.forEach((el, i) => {
                const rect = el.getBoundingClientRect();
                const x = rect.left + window.scrollX + rect.width / 2;
                const y = rect.top + window.scrollY + rect.height / 2;
                points.push(`${x},${y}`);

                // Number badge
                const badge = document.createElement('div');
                badge.className = 'absolute bg-blue-500 text-white text-[10px] font-bold w-5 h-5 flex items-center justify-center rounded-full border-2 border-white shadow-md z-[99999]';
                badge.style.left = `${x - 10}px`;
                badge.style.top = `${y - 10}px`;
                badge.textContent = `${i + 1}`;
                svg.appendChild(badge as any);
                
                // Outline
                const outline = document.createElement('div');
                outline.className = 'absolute border-2 border-blue-500/50 rounded pointer-events-none z-[99998]';
                outline.style.left = `${rect.left + window.scrollX}px`;
                outline.style.top = `${rect.top + window.scrollY}px`;
                outline.style.width = `${rect.width}px`;
                outline.style.height = `${rect.height}px`;
                svg.appendChild(outline as any);
            });

            if (points.length > 1) {
                const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
                polyline.setAttribute('points', points.join(' '));
                polyline.setAttribute('fill', 'none');
                polyline.setAttribute('stroke', '#3b82f6'); // blue-500
                polyline.setAttribute('stroke-width', '2');
                polyline.setAttribute('stroke-dasharray', '5,5');
                svg.insertBefore(polyline, svg.firstChild);
            }

            document.body.appendChild(svg);
        }
    };

    return (
        <div className="space-y-6 relative z-20 h-full flex flex-col">
            <div className="flex justify-between items-center border-b pb-2 mb-2">
                <h3 className={cn("font-extrabold text-sm uppercase tracking-widest flex items-center gap-2", isDark ? "text-orange-400 drop-shadow-[0_0_8px_rgba(251,146,60,0.8)]" : "text-orange-700")}>
                    <ScanEye className="w-5 h-5 text-orange-500" /> A11y Scanner
                </h3>
            </div>

            <p className={cn("text-[10px]", isDark ? "text-gray-400" : "text-slate-500")}>
                Traverses the DOM to find missing ARIA labels, empty alternative texts, and poorly structured semantics. Click "Scan UI" to run heuristics.
            </p>

            {/* Color Blindness Emulation */}
            <div className={cn("p-4 border rounded flex flex-col gap-3", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-orange-400" : "text-orange-600")}>
                        <Palette className="w-4 h-4" /> Color Blindness Emulator
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Applies SVG filters to the entire document to simulate various forms of color vision deficiency.</p>
                </div>
                <select
                    value={colorMode}
                    onChange={(e) => applyColorFilter(e.target.value)}
                    className={cn(
                        "w-full px-3 py-2 text-xs font-mono rounded border outline-none transition-colors",
                        isDark ? "bg-gray-900 border-gray-700 text-orange-200 focus:border-orange-500" : "bg-slate-50 border-slate-300 focus:border-orange-500"
                    )}
                >
                    <option value="none">Normal Vision (No Filter)</option>
                    <option value="protanopia">Protanopia (No Red)</option>
                    <option value="deuteranopia">Deuteranopia (No Green)</option>
                    <option value="tritanopia">Tritanopia (No Blue)</option>
                    <option value="achromatopsia">Achromatopsia (Full Monochromacy)</option>
                </select>
            </div>

            {/* Focus Order Tracer */}
            <div className={cn("p-4 border rounded flex items-center justify-between", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div>
                    <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-orange-400" : "text-orange-600")}>
                        <Route className="w-4 h-4" /> Focus Order Overlay
                    </h4>
                    <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Draws sequential paths between all tabbable elements on the page.</p>
                </div>
                <button
                    onClick={toggleFocusOrder}
                    className={cn(
                        "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                        focusOrderActive
                            ? (isDark ? "bg-orange-500/30 border-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.4)]" : "bg-orange-100 border-orange-500")
                            : (isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")
                    )}
                >
                    <div
                        className={cn(
                            "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                            focusOrderActive
                                ? (isDark ? "translate-x-6 bg-orange-400 shadow-[0_0_10px_#fb923c]" : "translate-x-6 bg-orange-500")
                                : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                        )}
                    />
                </button>
            </div>

            <div className={cn("p-4 border rounded relative overflow-hidden", isDark ? "bg-black/50 border-gray-800" : "bg-white border-slate-200")}>
                <div className="flex justify-between items-center z-10 relative">
                    <div>
                        <h4 className={cn("font-bold flex items-center gap-2 mb-1", isDark ? "text-orange-400" : "text-orange-600")}>
                            <AlertTriangle className="w-4 h-4" /> Live Overlay Highlight
                        </h4>
                        <p className={cn("text-[10px]", isDark ? "text-gray-500" : "text-slate-500")}>Draws flashing borders around elements that fail the scan.</p>
                    </div>
                    <button
                        onClick={toggleOverlay}
                        className={cn(
                            "relative w-12 h-6 shrink-0 rounded-full transition-colors duration-300 focus:outline-none border-2",
                            overlayActive
                                ? (isDark ? "bg-orange-500/30 border-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.4)]" : "bg-orange-100 border-orange-500")
                                : (isDark ? "bg-gray-800 border-gray-600" : "bg-slate-200 border-slate-300")
                        )}
                    >
                        <div
                            className={cn(
                                "absolute top-0.5 left-0.5 w-4 h-4 rounded-full shadow-md transition-transform duration-300",
                                overlayActive
                                    ? (isDark ? "translate-x-6 bg-orange-400 shadow-[0_0_10px_#fb923c]" : "translate-x-6 bg-orange-500")
                                    : (isDark ? "translate-x-0 bg-gray-400" : "translate-x-0 bg-white")
                            )}
                        />
                    </button>
                </div>
            </div>

            <div className="flex gap-2">
                <button
                    onClick={scanDOM}
                    className={cn(
                        "w-full py-2 flex items-center justify-center gap-2 rounded text-xs font-bold uppercase tracking-widest transition-all",
                        isDark 
                            ? "bg-gray-900 border border-orange-500/30 text-orange-400 hover:bg-orange-900/40 hover:border-orange-500/60 shadow-[0_0_15px_rgba(249,115,22,0.1)]" 
                            : "bg-orange-50 border border-orange-200 text-orange-700 hover:bg-orange-100"
                    )}
                >
                    <ScanEye className="w-4 h-4" /> Scan Current UI
                </button>
            </div>

            <div className="flex-1 overflow-auto space-y-3 pr-1">
                <AnimatePresence>
                    {violations.length === 0 && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={cn("p-8 text-center italic text-xs border rounded border-dashed", isDark ? "border-gray-800 text-gray-500" : "border-slate-300 text-slate-400")}>
                            No violations found, or scan not run yet.
                        </motion.div>
                    )}
                    {violations.map(v => (
                        <motion.div 
                            key={v.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className={cn(
                                "border rounded overflow-hidden text-left w-full",
                                isDark ? "border-red-900/50 bg-black/50" : "border-red-100 bg-red-50/50"
                            )}
                        >
                            <div className={cn("p-2 border-b flex items-start gap-2", isDark ? "bg-red-900/20 border-red-900/50" : "bg-red-50 border-red-100")}>
                                {v.type === 'missing_alt' ? <MonitorOff className="w-4 h-4 flex-shrink-0 text-red-500 mt-0.5" /> : <ShieldAlert className="w-4 h-4 flex-shrink-0 text-red-500 mt-0.5" />}
                                <span className={cn("text-xs font-bold", isDark ? "text-red-400" : "text-red-700")}>
                                    {v.message}
                                </span>
                            </div>
                            <div className="p-3 bg-black">
                                <code className="text-[10px] text-green-400 font-mono break-all whitespace-pre-wrap">
                                    {v.snippet.length > 90 ? v.snippet.substring(0, 90) + '...' : v.snippet}
                                </code>
                            </div>
                            <div className={cn("px-2 py-1.5 border-t text-right", isDark ? "border-gray-800" : "border-slate-200")}>
                                <button
                                    onClick={() => scrollToElem(v.element)}
                                    className="text-[10px] uppercase font-bold text-blue-500 hover:underline inline-flex items-center gap-1"
                                >
                                    Focus Element
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
            
        </div>
    );
}
