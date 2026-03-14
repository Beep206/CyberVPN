import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n/config';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';

export function generateStaticParams() {
    return locales.map((locale) => ({ locale }));
}

export default async function DocsLayout({
    children,
    params
}: {
    children: React.ReactNode;
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    setRequestLocale(locale);

    return (
        <div className="flex flex-col min-h-screen selection:bg-neon-cyan selection:text-black">
            <TerminalHeader />
            <div className="flex-1 relative">
                {children}
            </div>
            <Footer />
        </div>
    );
}
