import { LandingHero } from '@/widgets/landing-hero';
import { LandingFeatures } from '@/widgets/landing-features';
import { TerminalHeader } from '@/widgets/terminal-header';

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;

    return (
        <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
            <TerminalHeader />
            <LandingHero />
            <LandingFeatures />
            {/* Footer could go here */}
        </main>
    );
}
