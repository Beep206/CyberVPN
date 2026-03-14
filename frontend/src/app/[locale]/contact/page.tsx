import { getTranslations } from 'next-intl/server';
import { ContactTerminal } from '@/widgets/contact-terminal';
import { ScrambleText } from '@/shared/ui/scramble-text';
import { Terminal } from 'lucide-react';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Contact' });

    return {
        title: `${t('title')} | CyberVPN`,
        description: t('subtitle'),
    };
}

export default async function ContactPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Contact' });

    return (
        <main className="min-h-[calc(100vh-80px)] flex flex-col items-center justify-center p-6 lg:p-12 relative overflow-hidden">
            {/* Background Effects */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[60vw] bg-neon-cyan/5 rounded-full blur-[120px]" />
                <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-[0.03]" />
            </div>

            {/* Header Content */}
            <div className="relative z-10 w-full max-w-4xl text-center mb-12">
                <p className="font-cyber text-neon-cyan tracking-[0.2em] mb-4 flex items-center justify-center gap-2 text-sm">
                    <Terminal className="w-4 h-4" /> &gt; {t('subtitle')}
                </p>
                <h1 className="text-4xl md:text-5xl font-display font-black text-foreground drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                    <ScrambleText text={t('title')} />
                </h1>
            </div>

            {/* The Main Terminal Interface */}
            <div className="relative z-10 w-full max-w-3xl">
                <ContactTerminal terminalName={t('terminalName')} />
            </div>

        </main>
    );
}
