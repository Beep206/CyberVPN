'use client';

import { Bell, Search, Wifi } from 'lucide-react';
import { useEffect, useState, useTransition } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';
import { useRouter } from '@/i18n/navigation';
import { locales } from '@/i18n/config';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { LanguageSelector } from '@/features/language-selector';
import { cn } from '@/lib/utils';

export function TerminalHeader() {
    const [time, setTime] = useState<string>('');
    const [fps, setFps] = useState<number | null>(null);
    const [ping, setPing] = useState<number | null>(null);
    const locale = useLocale();
    const t = useTranslations('Header');
    const router = useRouter();
    const pathname = usePathname();
    const [isPending, startTransition] = useTransition();

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
        let rafId = 0;

        const loop = (now: number) => {
            frameCount += 1;
            const delta = now - lastTime;

            if (delta >= 1000) {
                setFps(Math.round((frameCount * 1000) / delta));
                frameCount = 0;
                lastTime = now;
            }

            rafId = requestAnimationFrame(loop);
        };

        rafId = requestAnimationFrame(loop);
        return () => cancelAnimationFrame(rafId);
    }, []);

    useEffect(() => {
        let active = true;

        const measurePing = async () => {
            const start = performance.now();
            try {
                await fetch('/favicon.ico', { method: 'HEAD', cache: 'no-store' });
            } catch { }
            const duration = Math.round(performance.now() - start);
            if (active) {
                setPing(duration);
            }
        };

        measurePing();
        const interval = setInterval(measurePing, 5000);
        return () => {
            active = false;
            clearInterval(interval);
        };
    }, []);

    return (
        <header className="sticky top-0 z-30 flex h-16 w-full items-center gap-4 bg-terminal-surface/80 backdrop-blur-xl border-b border-grid-line/30 px-6 transition-all">
            <div className="flex flex-1 items-center gap-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-grid-line/30 bg-black/20 text-muted-foreground hover:text-foreground">
                    <Search className="h-4 w-4" />
                </div>

                {/* Cypher Text Status */}
                <div className="hidden md:flex items-center text-xs font-cyber text-muted-foreground/50">
                    <span className="mr-1">{t('systemLabel')}:</span>
                    <CypherText text={t('integrity')} className="text-neon-cyan" />
                    <span className="mx-2">|</span>
                    <span className="mr-1">{t('encryptionLabel')}:</span>
                    <CypherText text={t('encryptionValue')} className="text-neon-purple" />
                </div>
            </div>

            <div className="flex items-center gap-4">
                <div className="hidden md:flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                    <div className="flex items-center gap-1">
                        <span className="text-muted-foreground/60">{t('fps')}</span>
                        <span className="text-neon-cyan">{fps ?? '--'}</span>
                    </div>
                    <span className="text-muted-foreground/30">|</span>
                    <div className="flex items-center gap-1">
                        <span className="text-muted-foreground/60">{t('ping')}</span>
                        <span className="text-matrix-green">{ping !== null ? `${ping}ms` : '--'}</span>
                    </div>
                </div>

                {/* Network Pulse */}
                <div className="flex items-center gap-2 text-xs font-mono text-matrix-green bg-matrix-green/10 px-3 py-1 rounded-full border border-matrix-green/30">
                    <Wifi className="h-3 w-3 animate-pulse" />
                    <span>{t('netUplink')}</span>
                </div>

                <div className="flex items-center gap-2">
                    <span className="hidden md:inline text-[10px] font-mono text-muted-foreground/60">
                        {t('language')}
                    </span>
                    <LanguageSelector />
                </div>

                <div className="font-cyber text-sm text-neon-cyan/80 min-w-[100px] text-right">
                    {time || "--:--:--"}
                </div>

                <button className="relative rounded-full p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground">
                    <Bell className="h-5 w-5" />
                    <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-neon-pink shadow-[0_0_8px_#ff0055]" />
                </button>
            </div>
        </header>
    );
}
