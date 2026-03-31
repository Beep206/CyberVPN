import type { BreadcrumbList, SoftwareApplication } from 'schema-dts';
import { getTranslations } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  buildBreadcrumbListStructuredData,
  buildSoftwareApplicationStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { DownloadDashboard } from '@/widgets/download/download-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Download' });

    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    }, {
        locale,
        canonicalPath: '/download',
        routeType: 'public',
    });
}

export default async function DownloadPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Download' });
    const pageTitle = t('title');
    const appStructuredData = buildSoftwareApplicationStructuredData({
        locale,
        path: '/download',
        title: 'CyberVPN',
        description: t('subtitle'),
        applicationCategory: 'SecurityApplication',
        operatingSystems: [
            t('platforms.windows'),
            t('platforms.macos'),
            t('platforms.linux'),
            t('platforms.ios'),
            t('platforms.android'),
        ],
        featureList: [
            t('terminal.button'),
            t('terminal.ready'),
            t('changelog.title'),
        ],
        downloadPath: '/download',
    });
    const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
        locale,
        items: [
            { name: 'Home', path: '/' },
            { name: pageTitle, path: '/download' },
        ],
    });

    return (
        <>
            <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
                <PublicTerminalHeader locale={locale} />
                
                <main className="flex-1 relative w-full h-full flex flex-col">
                    <DownloadDashboard />
                </main>

                <div className="relative z-20 bg-background/80 backdrop-blur-md border-t border-white/5">
                    <Footer locale={locale} />
                </div>
            </div>

            <JsonLd<SoftwareApplication> data={appStructuredData} />
            <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
        </>
    );
}
