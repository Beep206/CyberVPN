import type { SoftwareApplication } from 'schema-dts';
import { getTranslations } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import { buildSoftwareApplicationStructuredData } from '@/shared/lib/structured-data';
import { LandingHero } from '@/widgets/landing-hero';
import { LandingFeatures } from '@/widgets/landing-features';
import { LandingTechnical } from '@/widgets/landing-technical';
import { SpeedTunnel } from '@/widgets/speed-tunnel';
import { QuickStart } from '@/widgets/quick-start';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Landing.hero' });

    return withSiteMetadata({
        title: `${t('title')} ${t('titleHighlight')} | CyberVPN`,
        description: t('subtitle'),
    }, {
        locale,
        canonicalPath: '/',
        routeType: 'public',
    });
}

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const [heroT, featuresT] = await Promise.all([
        getTranslations({ locale, namespace: 'Landing.hero' }),
        getTranslations({ locale, namespace: 'Landing.features' }),
    ]);
    const softwareStructuredData = buildSoftwareApplicationStructuredData({
        locale,
        path: '/',
        title: 'CyberVPN',
        description: heroT('subtitle'),
        applicationCategory: 'SecurityApplication',
        operatingSystems: ['Telegram Bot', 'iOS', 'Android', 'Windows', 'macOS', 'Linux'],
        featureList: [
            featuresT('stealth.title'),
            featuresT('backbone.title'),
            featuresT('ram.title'),
            featuresT('routing.title'),
            featuresT('multiplatform.title'),
            featuresT('protocols.title'),
        ],
        downloadPath: '/download',
    });

    return (
        <>
            <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
                <PublicTerminalHeader />
                <LandingHero />
                <LandingFeatures />
                <LandingTechnical />
                <SpeedTunnel />
                <QuickStart />
                <Footer />
            </main>

            <JsonLd<SoftwareApplication> data={softwareStructuredData} />
        </>
    );
}
