import { getTranslations } from 'next-intl/server';
import { AnalyticsClient } from './components/AnalyticsClient';

export default async function AnalyticsPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Analytics' });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-display text-neon-cyan mb-2">
                        {t('title') || 'Analytics Dashboard'}
                    </h1>
                    <p className="text-muted-foreground font-mono">
                        {t('subtitle') || 'Monitor your platform performance and growth metrics'}
                    </p>
                </div>
            </div>

            <AnalyticsClient />
        </div>
    );
}
