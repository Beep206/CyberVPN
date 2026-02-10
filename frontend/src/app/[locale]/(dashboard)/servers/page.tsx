import { getTranslations } from 'next-intl/server';
import { ServersDataGrid } from '@/widgets/servers-data-grid';
import { ErrorBoundary } from '@/shared/ui/error-boundary';

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
                    <h1 className="text-3xl font-display text-foreground tracking-widest">{t('title')}</h1>
                    <p className="text-muted-foreground font-mono mt-2">{t('subtitle')}</p>
                </div>
                <div className="text-right">
                    <div className="text-sm font-cyber text-neon-cyan">{t('globalStatus', { status: t('globalStatusValue') })}</div>
                    <div className="text-xs text-muted-foreground mt-1">{t('lastSync', { time: '14s' })}</div>
                </div>
            </div>

            <ErrorBoundary label="Server Data Grid">
                <ServersDataGrid />
            </ErrorBoundary>
        </div>
    );
}
