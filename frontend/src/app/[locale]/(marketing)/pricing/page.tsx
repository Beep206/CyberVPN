import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';
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
    });
}

export default function PricingPage() {

    return (
        <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
            <TerminalHeader />
            
            <main className="flex-1 relative w-full h-full flex flex-col">
                <PricingDashboard />
            </main>

            <div className="relative z-20 bg-background/80 backdrop-blur-md border-t border-white/5">
                <Footer />
            </div>
        </div>
    );
}
