import { getTranslations } from 'next-intl/server';
import { MonitoringClient } from './components/MonitoringClient';

export default async function MonitoringPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Monitoring' });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-display text-neon-cyan mb-2">
                        {t('title') || 'System Monitoring'}
                    </h1>
                    <p className="text-muted-foreground font-mono">
                        {t('subtitle') || 'Real-time system health and performance metrics'}
                    </p>
                </div>
            </div>

            <MonitoringClient />
        </div>
    );
}
