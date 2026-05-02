import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CypherText } from '../../../shared/ui/atoms/cypher-text';
import { Activity, Zap } from 'lucide-react';

interface FpsPingMeterProps {
    ping: number | null | undefined;
    isScanning?: boolean;
}

export function FpsPingMeter({ ping, isScanning }: FpsPingMeterProps) {
    const { t } = useTranslation();
    const [fps, setFps] = useState(60);

    // Decorative FPS logic
    useEffect(() => {
        const interval = setInterval(() => {
            // Fluctuates between 58 and 62 typically, dipping occasionally if hypothetically under load
            setFps(Math.floor(Math.random() * (62 - 58 + 1)) + 58);
        }, 1500);
        return () => clearInterval(interval);
    }, []);

    const pingValue = ping ? `${ping}ms` : '---';
    const pingColor = !ping ? 'var(--muted-foreground)' : ping < 100 ? 'var(--color-matrix-green)' : ping < 200 ? 'var(--color-neon-cyan)' : 'var(--color-neon-pink)';

    return (
        <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-4 rounded-[1.25rem] border border-[color:var(--border)] bg-[color:var(--panel-subtle)]/72 px-4 py-3 shadow-[var(--panel-shadow)]">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border/50 bg-[color:var(--panel-surface)]">
                    <Activity size={18} className="text-muted-foreground" />
                </div>
                <div>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                        {t('dashboard.fpsCounter', 'Render FPS')}
                    </div>
                    <div className="mt-1 font-mono text-lg font-bold text-foreground">
                        <CypherText text={fps.toString()} trigger={fps} className="text-[color:var(--color-neon-cyan)]" />
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-4 rounded-[1.25rem] border border-[color:var(--border)] bg-[color:var(--panel-subtle)]/72 px-4 py-3 shadow-[var(--panel-shadow)] text-left">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border/50 bg-[color:var(--panel-surface)]">
                    <Zap size={18} style={{ color: pingColor }} className={isScanning ? 'animate-pulse' : ''} />
                </div>
                <div>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                        {t('dashboard.latency', 'Latency')}
                    </div>
                    <div className="mt-1 font-mono text-lg font-bold" style={{ color: pingColor }}>
                        {isScanning ? (
                            <span className="animate-pulse">{t('dashboard.scanning', 'Scn...')}</span>
                        ) : (
                            pingValue
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
