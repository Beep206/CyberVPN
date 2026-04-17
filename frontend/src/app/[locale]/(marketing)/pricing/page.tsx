import type { BreadcrumbList, SoftwareApplication } from 'schema-dts';
import { getTranslations } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  buildBreadcrumbListStructuredData,
  buildSoftwareApplicationStructuredData,
} from '@/shared/lib/structured-data';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { getPublicPricingCatalog } from '@/widgets/pricing/catalog';
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
    const catalog = await getPublicPricingCatalog();
    const pageTitle = t('title');
    const appStructuredData = buildSoftwareApplicationStructuredData({
        locale,
        path: '/pricing',
        title: 'CyberVPN',
        description: t('subtitle'),
        applicationCategory: 'SecurityApplication',
        operatingSystems: ['Telegram Bot', 'iOS', 'Android', 'Windows', 'macOS', 'Linux'],
        featureList: catalog.plans.map((plan) => t(`tiers.${plan.code}.description`)),
        offers: catalog.plans.map((plan) => {
            const lowestPrice = Math.min(...plan.periods.map((period) => period.price_usd));

            return {
                name: plan.display_name,
                description: t(`tiers.${plan.code}.description`),
                price: String(lowestPrice),
                priceCurrency: 'USD',
                url: '/pricing',
            };
        }),
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
                    <PricingDashboard catalog={catalog} />
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
