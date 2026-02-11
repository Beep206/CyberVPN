import type { Metadata } from "next";
import { Orbitron, JetBrains_Mono, Share_Tech_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { locales } from "@/i18n/config";
import "../globals.css";

export function generateStaticParams() {
    return locales.map((locale) => ({ locale }));
}

const orbitron = Orbitron({
    variable: "--font-display",
    subsets: ["latin"],
    display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
    variable: "--font-mono",
    subsets: ["latin"],
    display: "swap",
});

const shareTechMono = Share_Tech_Mono({
    weight: "400",
    variable: "--font-cyber",
    subsets: ["latin"],
    display: "swap",
});

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
    const { locale } = await params;
    return {
        title: "VPN Command Center",
        description: "Advanced Cyberpunk VPN Admin Interface",
        metadataBase: new URL('https://vpn-admin.example.com'),
        alternates: {
            languages: Object.fromEntries(
                locales.map((l) => [l, `/${l}`])
            ),
            canonical: `/${locale}`,
        },
    };
}

import { JsonLd } from '@/shared/lib/json-ld';
import type { Organization, WebSite } from 'schema-dts';
import { ThemeProvider } from "@/app/providers/theme-provider";
import { AuthProvider } from "@/app/providers/auth-provider";
import { QueryProvider } from "@/app/providers/query-provider";
import { SmoothScrollProvider } from "@/app/providers/smooth-scroll-provider";
import { DevPanel } from "@/features/dev/dev-panel";
import { SkipNavLink } from "@/shared/ui/atoms/skip-nav-link";
import { WebVitalsReporter } from "@/shared/ui/atoms/web-vitals-reporter";

export default async function RootLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    setRequestLocale(locale);
    const messages = await getMessages({ locale });
    return (
        <html lang={locale} suppressHydrationWarning>
            <body
                suppressHydrationWarning
                className={`
          ${orbitron.variable} 
          ${jetbrainsMono.variable} 
          ${shareTechMono.variable} 
          antialiased bg-terminal-bg text-foreground min-h-screen overflow-hidden selection:bg-neon-cyan/30
        `}
            >
                <ThemeProvider
                    attribute="class"
                    defaultTheme="system"
                    enableSystem
                    disableTransitionOnChange
                >
                    <NextIntlClientProvider locale={locale} messages={messages}>
                        <AuthProvider>
                          <QueryProvider>
                            <SmoothScrollProvider>
                                <SkipNavLink />
                                <div className="relative z-10 h-full w-full">
                                    {children}
                                </div>
                            </SmoothScrollProvider>
                          </QueryProvider>
                        </AuthProvider>
                    </NextIntlClientProvider>
                    {/* Background scanline effect and glow can be global or part of specific layouts */}
                    <div className="pointer-events-none fixed inset-0 z-50 scanline opacity-20" />
                    <DevPanel />
                    <WebVitalsReporter />
                </ThemeProvider>
                <JsonLd<Organization>
                    data={{
                        '@context': 'https://schema.org',
                        '@type': 'Organization',
                        name: 'CyberVPN',
                        url: 'https://cybervpn.com',
                        logo: 'https://cybervpn.com/logo.png',
                        sameAs: [
                            'https://t.me/cybervpn',
                        ],
                    }}
                />
                <JsonLd<WebSite>
                    data={{
                        '@context': 'https://schema.org',
                        '@type': 'WebSite',
                        name: 'CyberVPN',
                        url: 'https://cybervpn.com',
                        potentialAction: {
                            '@type': 'SearchAction',
                            target: 'https://cybervpn.com/search?q={search_term_string}',
                            // @ts-expect-error - schema.org query-input format
                            'query-input': 'required name=search_term_string',
                        },
                    }}
                />
            </body>
        </html>
    );
}
