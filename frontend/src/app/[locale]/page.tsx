import { LandingHero } from '@/widgets/landing-hero';
import { LandingFeatures } from '@/widgets/landing-features';
import { SpeedTunnel } from '@/widgets/speed-tunnel';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
    await params;

    return (
        <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
            <TerminalHeader />
            <LandingHero />
            <LandingFeatures />
            <SpeedTunnel />
            <Footer />
        </main>
    );
}
