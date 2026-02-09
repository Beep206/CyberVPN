'use client';

import { useTranslations } from 'next-intl';

/**
 * SkipNavLink - A visually hidden link that becomes visible on keyboard focus.
 * Allows keyboard users to skip directly to the main content area,
 * bypassing repeated navigation elements.
 *
 * Renders as an absolutely positioned link that slides into view
 * with a cyberpunk neon-cyan focus ring when focused via keyboard.
 */
export function SkipNavLink() {
    const t = useTranslations('A11y');

    return (
        <a
            href="#main-content"
            className="
                sr-only
                focus:not-sr-only
                focus:fixed
                focus:top-4
                focus:z-[100]
                focus:px-6
                focus:py-3
                focus:font-mono
                focus:text-sm
                focus:tracking-wider
                focus:text-terminal-bg
                focus:bg-neon-cyan
                focus:rounded-sm
                focus:shadow-[0_0_20px_var(--color-neon-cyan),0_0_40px_var(--color-neon-cyan)]
                focus:outline-hidden
                focus:ring-2
                focus:ring-neon-cyan
                focus:ring-offset-2
                focus:ring-offset-terminal-bg
                focus:inset-inline-start-4
                motion-safe:focus:animate-pulse
            "
            aria-label={t('skipToMainContent')}
        >
            {t('skipToMainContent')}
        </a>
    );
}
