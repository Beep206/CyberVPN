'use client';

import { motion } from 'motion/react';
import { cn } from '@/lib/utils';
import { MagneticButton } from '@/shared/ui/magnetic-button';

// Telegram icon SVG
const TELEGRAM_ICON = (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
        <path d="M11.944 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0a12 12 0 00-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 01.171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" fill="#0088CC" />
    </svg>
);

// Social provider icons (inline SVGs for best performance)
const PROVIDERS = {
    google: {
        name: 'Google',
        icon: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
        ),
        colors: 'hover:bg-white/10 hover:border-white/30',
    },
    github: {
        name: 'GitHub',
        icon: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
            </svg>
        ),
        colors: 'hover:bg-[#24292e]/80 hover:border-[#24292e]',
    },
    discord: {
        name: 'Discord',
        icon: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" fill="#5865F2" />
            </svg>
        ),
        colors: 'hover:bg-[#5865F2]/20 hover:border-[#5865F2]',
    },
    apple: {
        name: 'Apple',
        icon: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
            </svg>
        ),
        colors: 'hover:bg-white/10 hover:border-white/30',
    },
    microsoft: {
        name: 'Microsoft',
        icon: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z" fill="#00A4EF" />
            </svg>
        ),
        colors: 'hover:bg-[#00A4EF]/20 hover:border-[#00A4EF]',
    },
    twitter: {
        name: 'X',
        icon: (
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
        ),
        colors: 'hover:bg-white/10 hover:border-white/30',
    },
};

// Row groupings for compact layout below Telegram
const COMPACT_ROW_1: Array<keyof typeof PROVIDERS> = ['google', 'github', 'discord'];
const COMPACT_ROW_2: Array<keyof typeof PROVIDERS> = ['apple', 'microsoft', 'twitter'];

interface SocialAuthButtonsProps {
    onProviderClick?: (provider: string) => void;
    disabled?: boolean;
    className?: string;
}

export function SocialAuthButtons({
    onProviderClick,
    disabled = false,
    className,
}: SocialAuthButtonsProps) {
    return (
        <div className={cn("flex flex-col gap-3", className)}>
            {/* Telegram — primary position, full-width */}
            <MagneticButton className="w-full">
                <motion.button
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    type="button"
                    onClick={() => onProviderClick?.('telegram')}
                    disabled={disabled}
                    className={cn(
                        "w-full flex items-center justify-center gap-2",
                        "py-3.5 px-4 rounded-lg",
                        "bg-[#0088CC]/15",
                        "border border-[#0088CC]/40",
                        "text-[#0088CC]",
                        "font-mono text-sm font-semibold",
                        "transition-all duration-200",
                        "cursor-pointer",
                        "hover:bg-[#0088CC]/25 hover:border-[#0088CC]/60",
                        disabled && "opacity-50 cursor-not-allowed",
                        "focus:outline-none focus:ring-2 focus:ring-[#0088CC]/50 focus:ring-offset-2 focus:ring-offset-terminal-bg"
                    )}
                    aria-label="Sign in with Telegram"
                >
                    {TELEGRAM_ICON}
                    <span>Telegram</span>
                </motion.button>
            </MagneticButton>

            {/* Separator between Telegram and other providers */}
            <div className="relative my-1">
                <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-grid-line/20" />
                </div>
                <div className="relative flex justify-center text-xs">
                    <span className="px-3 bg-terminal-surface dark:bg-transparent text-muted-foreground/50 font-mono uppercase tracking-wider text-[10px]">
                        or
                    </span>
                </div>
            </div>

            {/* Row 1: Google, GitHub, Discord */}
            <div className="flex gap-3">
                {COMPACT_ROW_1.map((provider, index) => {
                    const { name, icon, colors } = PROVIDERS[provider];
                    return (
                        <MagneticButton key={provider} className="flex-1">
                            <motion.button
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.05 * (index + 1), duration: 0.3 }}
                                type="button"
                                onClick={() => onProviderClick?.(provider)}
                                disabled={disabled}
                                className={cn(
                                    "w-full flex items-center justify-center gap-2",
                                    "py-3 px-4 rounded-lg",
                                    "bg-terminal-bg/50 dark:bg-black/40",
                                    "border border-grid-line/30",
                                    "text-muted-foreground",
                                    "font-mono text-sm",
                                    "transition-all duration-200",
                                    "cursor-pointer",
                                    colors,
                                    disabled && "opacity-50 cursor-not-allowed",
                                    "focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 focus:ring-offset-2 focus:ring-offset-terminal-bg"
                                )}
                                aria-label={`Sign in with ${name}`}
                            >
                                {icon}
                                <span className="hidden sm:inline">{name}</span>
                            </motion.button>
                        </MagneticButton>
                    );
                })}
            </div>

            {/* Row 2: Apple, Microsoft, X */}
            <div className="flex gap-3">
                {COMPACT_ROW_2.map((provider, index) => {
                    const { name, icon, colors } = PROVIDERS[provider];
                    return (
                        <MagneticButton key={provider} className="flex-1">
                            <motion.button
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.05 * (index + 4), duration: 0.3 }}
                                type="button"
                                onClick={() => onProviderClick?.(provider)}
                                disabled={disabled}
                                className={cn(
                                    "w-full flex items-center justify-center gap-2",
                                    "py-3 px-4 rounded-lg",
                                    "bg-terminal-bg/50 dark:bg-black/40",
                                    "border border-grid-line/30",
                                    "text-muted-foreground",
                                    "font-mono text-sm",
                                    "transition-all duration-200",
                                    "cursor-pointer",
                                    colors,
                                    disabled && "opacity-50 cursor-not-allowed",
                                    "focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 focus:ring-offset-2 focus:ring-offset-terminal-bg"
                                )}
                                aria-label={`Sign in with ${name}`}
                            >
                                {icon}
                                <span className="hidden sm:inline">{name}</span>
                            </motion.button>
                        </MagneticButton>
                    );
                })}
            </div>
        </div>
    );
}

// Divider with "or" text
export function AuthDivider({ text = 'or' }: { text?: string }) {
    return (
        <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-grid-line/30" />
            </div>
            <div className="relative flex justify-center text-xs">
                <span className="px-4 bg-terminal-surface dark:bg-transparent text-muted-foreground font-mono uppercase tracking-wider">
                    {text}
                </span>
            </div>
        </div>
    );
}
