import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';

interface TrafficData {
    time: string;
    up: number;
    down: number;
}

interface TrafficGraphProps {
    data: TrafficData[];
}

export function TrafficGraph({ data }: TrafficGraphProps) {
    const { t } = useTranslation();
    // Format bytes to KB/s or MB/s
    const formatSpeed = (bytes: number) => {
        if (bytes === 0) return '0 B/s';
        const k = 1024;
        const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="w-full h-64 bg-black/20 rounded-xl border border-border/40 p-4">
            <h3 className="text-sm font-bold tracking-widest text-muted-foreground mb-4 uppercase flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[var(--color-matrix-green)] animate-pulse" />
                {t('dashboard.networkTraffic')}
            </h3>
            <div className="w-full h-[calc(100%-2rem)]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorDown" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--color-matrix-green)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="var(--color-matrix-green)" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="colorUp" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--color-neon-cyan)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="var(--color-neon-cyan)" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis 
                            dataKey="time" 
                            hide 
                        />
                        <YAxis 
                            tickFormatter={formatSpeed} 
                            axisLine={false} 
                            tickLine={false} 
                            tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                            width={80}
                            orientation="right"
                        />
                        <Tooltip 
                            contentStyle={{ 
                                backgroundColor: 'rgba(0,0,0,0.8)', 
                                border: '1px solid var(--border)',
                                borderRadius: '8px',
                                fontSize: '12px',
                                fontFamily: 'monospace'
                            }}
                            formatter={(value: any) => formatSpeed(Number(value))}
                        />
                        <Area 
                            type="monotone" 
                            dataKey="down" 
                            stroke="var(--color-matrix-green)" 
                            strokeWidth={2}
                            fillOpacity={1} 
                            fill="url(#colorDown)" 
                            name={t('dashboard.download')}
                            isAnimationActive={false}
                        />
                        <Area 
                            type="monotone" 
                            dataKey="up" 
                            stroke="var(--color-neon-cyan)" 
                            strokeWidth={2}
                            fillOpacity={1} 
                            fill="url(#colorUp)" 
                            name={t('dashboard.upload')}
                            isAnimationActive={false}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
