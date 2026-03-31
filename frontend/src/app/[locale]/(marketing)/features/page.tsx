import type { BreadcrumbList, SoftwareApplication } from 'schema-dts';
import { getTranslations } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  buildBreadcrumbListStructuredData,
  buildSoftwareApplicationStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { FeaturesDashboard } from '@/widgets/features/features-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Features' });
    
    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('description'),
    }, {
        locale,
        canonicalPath: '/features',
        routeType: 'public',
    });
}

export default async function FeaturesPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Features' });
    const pageTitle = t('title');
    const appStructuredData = buildSoftwareApplicationStructuredData({
        locale,
        path: '/features',
        title: 'CyberVPN',
        description: t('description'),
        applicationCategory: 'SecurityApplication',
        operatingSystems: ['Telegram Bot', 'iOS', 'Android', 'Windows', 'macOS', 'Linux'],
        featureList: [
            t('features.quantum.title'),
            t('features.multihop.title'),
            t('features.obfuscation.title'),
            t('features.killswitch.title'),
        ],
    });
    const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
        locale,
        items: [
            { name: 'Home', path: '/' },
            { name: pageTitle, path: '/features' },
        ],
    });

    return (
        <>
            <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-cyan/30 flex flex-col font-mono overflow-x-hidden">
                <PublicTerminalHeader />
                
                <section className="flex-1 relative w-full pt-16">
                    <FeaturesDashboard/>
                </section>
                
                <Footer />
            </main>

            <JsonLd<SoftwareApplication> data={appStructuredData} />
            <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
        </>
    );
}
