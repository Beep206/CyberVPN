import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n/config';

export function generateStaticParams() {
    return locales.map((locale) => ({ locale }));
}

export default async function HelpLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    setRequestLocale(locale);

    return (
        <div className="flex-1 flex flex-col min-h-screen">
            {children}
        </div>
    );
}
