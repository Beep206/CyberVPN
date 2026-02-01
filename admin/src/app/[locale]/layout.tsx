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

export const metadata: Metadata = {
    title: {
        default: "VPN Command Center",
        template: "%s | VPN Command Center",
    },
    description: "Advanced Cyberpunk VPN Admin Interface",
    metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
    alternates: {
        languages: Object.fromEntries(
            locales.map((locale) => [locale, `/${locale}`])
        ),
    },
    twitter: {
        card: 'summary_large_image',
        title: 'VPN Command Center',
        description: 'Advanced Cyberpunk VPN Admin Interface',
    },
};

import { ThemeProvider } from "@/app/providers/theme-provider";

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
                        <div className="relative z-10 h-full w-full">
                            {children}
                        </div>
                    </NextIntlClientProvider>
                    {/* Background scanline effect and glow can be global or part of specific layouts */}
                    <div className="pointer-events-none fixed inset-0 z-50 scanline opacity-20" />
                </ThemeProvider>
            </body>
        </html>
    );
}
