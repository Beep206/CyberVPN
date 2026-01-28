import { getTranslations } from 'next-intl/server';
import { ServersDataGrid } from '@/widgets/servers-data-grid';

export default async function ServersPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Servers' });
    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-center mb-8 bg-terminal-surface/30 p-6 rounded-xl border border-grid-line/30 backdrop-blur">
                <div>
                    <h1 className="text-3xl font-display text-white tracking-widest">{t('title')}</h1>
                    <p className="text-muted-foreground font-mono mt-2">{t('subtitle')}</p>
                </div>
                <div className="text-right">
                    <div className="text-sm font-cyber text-neon-cyan">{t('globalStatus', { status: t('globalStatusValue') })}</div>
                    <div className="text-xs text-muted-foreground mt-1">{t('lastSync', { time: '14s' })}</div>
                </div>
            </div>

            <ServersDataGrid />
        </div>
    );
}
