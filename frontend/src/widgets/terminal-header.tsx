'use client';

import { Wifi, Menu } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { LanguageSelector } from '@/features/language-selector';
import { ThemeToggle } from '@/features/theme-toggle';
import { NotificationDropdown } from "@/features/notifications/notification-dropdown";
import { MagneticButton } from "@/shared/ui/magnetic-button";

export function TerminalHeader() {
    const [time, setTime] = useState<string>('');
    const fpsRef = useRef<HTMLSpanElement>(null);
    const pingRef = useRef<HTMLSpanElement>(null);
    const t = useTranslations('Header');

    // Hydration fix for time
    useEffect(() => {
        const updateTime = () => setTime(new Date().toISOString().split('T')[1].split('.')[0] + ' UTC');
        updateTime();
        const timer = setInterval(updateTime, 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        let frameCount = 0;
        let lastTime = performance.now();

        const countFrame = () => {
            frameCount++;
            rafId = requestAnimationFrame(countFrame);
        };
        let rafId = requestAnimationFrame(countFrame);

        const display = setInterval(() => {
            const now = performance.now();
            const delta = now - lastTime;
            if (delta > 0 && fpsRef.current) {
                fpsRef.current.textContent = String(Math.round((frameCount * 1000) / delta));
            }
            frameCount = 0;
            lastTime = now;
        }, 1000);

        return () => {
            cancelAnimationFrame(rafId);
            clearInterval(display);
        };
    }, []);

    useEffect(() => {
        let active = true;

        const measurePing = async () => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            const start = performance.now();
            try {
                await fetch('/favicon.ico', { method: 'HEAD', cache: 'no-store', signal: controller.signal });
            } catch { /* ignore aborted and network errors */ }
            clearTimeout(timeoutId);
            const duration = Math.round(performance.now() - start);
            if (active && pingRef.current) {
                pingRef.current.textContent = `${duration}ms`;
            }
        };

        measurePing();
        const interval = setInterval(measurePing, 15000);
        return () => {
            active = false;
            clearInterval(interval);
        };
    }, []);

    return (
        <header className="sticky top-0 z-30 flex h-16 w-full items-center gap-4 bg-terminal-surface/95 backdrop-blur-xl border-b border-grid-line/50 shadow-sm dark:shadow-none px-6 pl-20 md:pl-6 transition-all">
            <div className="flex flex-1 items-center gap-4">
                <MagneticButton strength={15}>
                    <div
                        aria-hidden="true"
                        className="flex h-9 w-9 items-center justify-center rounded-lg border border-grid-line/30 bg-muted/50 text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                    >
                        <Menu className="h-4 w-4" />
                    </div>
                </MagneticButton>

                <div className="hidden md:flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                    <div className="flex items-center gap-1">
                        <span className="text-muted-foreground-low">{t('fps')}</span>
                        <span ref={fpsRef} className="text-neon-cyan">--</span>
                    </div>
                    <span className="text-muted-foreground-low">|</span>
                    <div className="flex items-center gap-1">
                        <span className="text-muted-foreground-low">{t('ping')}</span>
                        <span ref={pingRef} className="text-matrix-green">--</span>
                    </div>
                </div>

                {/* Network Pulse */}
                <div className="flex items-center gap-2 text-xs font-mono text-matrix-green bg-matrix-green/10 px-3 py-1 rounded-full border border-matrix-green/30">
                    <Wifi className="h-3 w-3 animate-pulse" />
                    <span className="hidden md:inline">{t('netUplink')}</span>
                </div>
            </div>

            <div className="flex items-center gap-4">

                <div className="flex items-center gap-2">
                    <ThemeToggle />

                    <LanguageSelector />
                </div>

                <div className="hidden md:block font-cyber text-sm text-neon-cyan/80 min-w-[100px] text-right">
                    {time || "--:--:--"}
                </div>

                <NotificationDropdown />
            </div>
        </header>
    );
}
