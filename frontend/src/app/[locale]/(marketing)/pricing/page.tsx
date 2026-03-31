import type { BreadcrumbList, SoftwareApplication } from 'schema-dts';
import { getTranslations } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  buildBreadcrumbListStructuredData,
  buildSoftwareApplicationStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { PricingDashboard } from '@/widgets/pricing/pricing-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Pricing' });

    return withSiteMetadata({
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    }, {
        locale,
        canonicalPath: '/pricing',
        routeType: 'public',
    });
}

export default async function PricingPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Pricing' });
    const pageTitle = t('title');
    const appStructuredData = buildSoftwareApplicationStructuredData({
        locale,
        path: '/pricing',
        title: 'CyberVPN',
        description: t('subtitle'),
        applicationCategory: 'SecurityApplication',
        operatingSystems: ['Telegram Bot', 'iOS', 'Android', 'Windows', 'macOS', 'Linux'],
        featureList: [
            t('tiers.basic.description'),
            t('tiers.pro.description'),
            t('tiers.elite.description'),
        ],
        offers: [
            {
                name: t('tiers.basic.name'),
                description: t('tiers.basic.description'),
                price: '0',
                url: '/pricing',
            },
            {
                name: t('tiers.pro.name'),
                description: t('tiers.pro.description'),
                price: '8.99',
                url: '/pricing',
            },
            {
                name: t('tiers.elite.name'),
                description: t('tiers.elite.description'),
                price: '15.99',
                url: '/pricing',
            },
        ],
    });
    const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
        locale,
        items: [
            { name: 'Home', path: '/' },
            { name: pageTitle, path: '/pricing' },
        ],
    });

    return (
        <>
            <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
                <PublicTerminalHeader locale={locale} />
                
                <main className="flex-1 relative w-full h-full flex flex-col">
                    <PricingDashboard />
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
