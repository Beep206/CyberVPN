import { AuthSceneLoader } from '@/features/auth/components/AuthSceneLoader';
import { MiniAppNavGuard } from '@/features/auth/components/MiniAppNavGuard';
import { TelegramMiniAppAuthProvider } from '@/features/auth/components/TelegramMiniAppAuthProvider';
import { ThemeToggle } from '@/features/theme-toggle';
import { LanguageSelector } from '@/features/language-selector';
import Link from 'next/link';
import { ArrowLeft, Shield } from 'lucide-react';

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="relative min-h-screen flex items-center justify-center bg-terminal-bg overflow-hidden">
            {/* 3D Background */}
            <AuthSceneLoader />

            {/* Overlay for text readability */}
            <div className="absolute inset-0 bg-terminal-bg/70 dark:bg-terminal-bg/50 z-[1]" />

            {/* Ambient glow effects */}
            <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-neon-cyan/10 dark:bg-neon-cyan/20 rounded-full blur-[120px] z-[1] pointer-events-none" />
            <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-neon-purple/10 dark:bg-neon-purple/20 rounded-full blur-[120px] z-[1] pointer-events-none" />

            {/* Top navigation bar — hidden in Telegram Mini App mode */}
            <MiniAppNavGuard>
                <nav className="fixed top-0 left-0 right-0 z-20 flex items-center justify-between p-4 md:p-6">
                    {/* Back to home */}
                    <Link
                        href="/"
                        aria-label="Back to home"
                        className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors font-mono text-sm group rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                    >
                        <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                        <span className="hidden sm:inline">back_to_home</span>
                    </Link>

                    {/* Logo */}
                    <Link href="/" aria-label="CyberVPN home" className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 group rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]">
                        <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 group-hover:border-neon-cyan/60 transition-colors">
                            <Shield className="h-4 w-4 text-neon-cyan" />
                        </div>
                        <span className="font-display text-lg font-bold tracking-tight text-foreground hidden sm:inline">
                            Cyber<span className="text-neon-cyan">VPN</span>
                        </span>
                    </Link>

                    {/* Controls */}
                    <div className="flex items-center gap-3">
                        <ThemeToggle />
                        <LanguageSelector />
                    </div>
                </nav>
            </MiniAppNavGuard>

            {/* Main content */}
            <main id="main-content" tabIndex={-1} className="relative z-10 w-full max-w-lg px-4 py-20 focus:outline-hidden">
                <TelegramMiniAppAuthProvider>
                    {children}
                </TelegramMiniAppAuthProvider>
            </main>

            {/* Bottom decorative line */}
            <div className="fixed bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent z-20" />
        </div>
    );
}
