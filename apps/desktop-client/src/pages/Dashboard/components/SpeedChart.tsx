import { useEffect, useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import { useTranslation } from 'react-i18next';

interface SpeedChartProps {
    downBytes: number;
    upBytes: number;
}

export function SpeedChart({ downBytes, upBytes }: SpeedChartProps) {
    const { t } = useTranslation();
    const [data, setData] = useState<{ time: string; download: number; upload: number }[]>([]);

    useEffect(() => {
        const interval = setInterval(() => {
            setData(prev => {
                const now = new Date().toLocaleTimeString('en-US', { hour12: false, second: '2-digit', minute: '2-digit' });
                const newData = [...prev, { time: now, download: downBytes / 1024, upload: upBytes / 1024 }];
                if (newData.length > 20) {
                    newData.shift(); // keep last 20 points
                }
                return newData;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [downBytes, upBytes]);

    const formatSpeed = (value: number) => {
        if (value > 1024) return `${(value / 1024).toFixed(1)} MB/s`;
        return `${value.toFixed(1)} KB/s`;
    };

    return (
        <div className="relative h-48 w-full overflow-hidden rounded-[1.25rem] border border-[color:var(--border)] bg-[color:var(--panel-subtle)]/72 p-4 shadow-[var(--panel-shadow)]">
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">{t('dashboard.networkTrafficChart', 'Network Activity')}</h3>
            <div className="absolute top-4 right-4 flex gap-4 text-[10px] font-semibold uppercase tracking-[0.22em]">
                <div className="flex items-center gap-1.5 text-[color:var(--color-neon-cyan)]">
                    <span className="h-2 w-2 rounded-full bg-[color:var(--color-neon-cyan)] shadow-[0_0_8px_var(--color-neon-cyan)]" /> Download
                </div>
                <div className="flex items-center gap-1.5 text-[color:var(--color-matrix-green)]">
                    <span className="h-2 w-2 rounded-full bg-[color:var(--color-matrix-green)] shadow-[0_0_8px_var(--color-matrix-green)]" /> Upload
                </div>
            </div>
            <div className="h-full w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorDownload" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--color-neon-cyan)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="var(--color-neon-cyan)" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorUpload" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--color-matrix-green)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="var(--color-matrix-green)" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="time" stroke="var(--muted-foreground)" fontSize={10} tickLine={false} axisLine={false} opacity={0.5} />
                        <YAxis stroke="var(--muted-foreground)" fontSize={10} tickLine={false} axisLine={false} opacity={0.5} tickFormatter={formatSpeed} />
                        <Tooltip
                            contentStyle={{ backgroundColor: 'var(--panel-surface)', border: '1px solid var(--border)', borderRadius: '0.625rem', fontSize: '12px' }}
                            itemStyle={{ color: 'var(--foreground)' }}
                            formatter={(value: any) => formatSpeed(Number(value))}
                        />
                        <Area type="monotone" dataKey="download" stroke="var(--color-neon-cyan)" strokeWidth={2} fillOpacity={1} fill="url(#colorDownload)" isAnimationActive={false} />
                        <Area type="monotone" dataKey="upload" stroke="var(--color-matrix-green)" strokeWidth={2} fillOpacity={1} fill="url(#colorUpload)" isAnimationActive={false} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
