import { getTranslations } from 'next-intl/server';
import { setRequestLocale } from 'next-intl/server';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { StatusDashboard } from '@/widgets/status/status-dashboard';
import { buildUptimeHistorySnapshot } from '@/widgets/status/uptime-history';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

const STATUS_HISTORY_ANCHOR = '2026-03-30T00:00:00.000Z';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Status' });

    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    }, {
        locale,
        canonicalPath: '/status',
        routeType: 'public',
    });
}

export default async function StatusPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    setRequestLocale(locale);
    const historyData = buildUptimeHistorySnapshot(new Date(STATUS_HISTORY_ANCHOR));

    return (
        <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
            <PublicTerminalHeader locale={locale} />
            
            <main className="flex-1 relative w-full h-full flex flex-col">
                <StatusDashboard historyData={historyData} />
            </main>

            {/* <Footer /> - The footer might overlap the 3D scene in full-height mode, 
                let's keep it but ensure the status dashboard manages its own bottom padding if needed. */}
            <div className="relative z-20 bg-background/80 backdrop-blur-md border-t border-white/5">
                <Footer locale={locale} />
            </div>
        </div>
    );
}
