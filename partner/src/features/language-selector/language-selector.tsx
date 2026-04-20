'use client';

import { startTransition, useState } from 'react';
import { useLocale } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import { Search, Check } from 'lucide-react';
import { CountryFlag } from '@/shared/ui/country-flag';
import { LANGUAGES } from '@/i18n/languages';
import { Modal } from '@/shared/ui/modal';
import { MagneticButton } from '@/shared/ui/magnetic-button';

export function LanguageSelector() {
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const currentLanguage = LANGUAGES.find(l => l.code === locale) || LANGUAGES[0];

    // ... (rest of the component logic)

    const query = searchQuery.toLowerCase();
    const filteredLanguages = LANGUAGES.filter(l =>
        l._searchName.includes(query) ||
        l._searchNative.includes(query) ||
        l._searchCode.includes(query)
    );

    const handleLanguageChange = (newLocale: string) => {
        startTransition(() => {
            router.replace(pathname, { locale: newLocale });
        });
        setIsOpen(false);
    };

    return (
        <>
            <MagneticButton strength={20}>
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setIsOpen(true)}
                    aria-label={`Select language: ${currentLanguage.name}`}
                    aria-haspopup="dialog"
                    aria-expanded={isOpen}
                    className="touch-target inline-flex items-center justify-center gap-2 rounded-lg border border-grid-line/30 bg-terminal-surface/30 px-3 text-muted-foreground transition-colors duration-300 group hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                >
                    <div className="flex items-center justify-center filter drop-shadow-[0_0_2px_rgba(255,255,255,0.5)]">
                        <CountryFlag
                            code={currentLanguage.countryCode}
                            className="rounded-[2px] w-6 h-auto" // w-6 is 24px
                        />
                    </div>
                    <span className="font-mono text-sm uppercase tracking-wider group-hover:text-neon-cyan transition-colors">
                        {currentLanguage.code.split('-')[1]}
                    </span>
                </motion.button>
            </MagneticButton>

            <Modal
                isOpen={isOpen}
                onClose={() => setIsOpen(false)}
                title="SELECT_LANGUAGE"
            >
                <div className="flex flex-col gap-4">
                    {/* Search Input */}
                    <div className="relative group">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-grid-line group-focus-within:text-neon-cyan transition-colors" size={18} />
                        <input
                            type="text"
                            placeholder="SEARCH_LANGUAGE..."
                            value={searchQuery}
                            onChange={(e) => startTransition(() => setSearchQuery(e.target.value))}
                            aria-label="Search languages"
                            inputMode="search"
                            spellCheck={false}
                            className="mobile-form-input touch-target w-full rounded-md border border-grid-line/30 bg-terminal-bg/50 py-2 pl-10 pr-4 font-mono text-foreground transition-all duration-300 placeholder:text-muted-foreground focus-visible:outline-hidden focus-visible:border-neon-cyan focus-visible:shadow-[0_0_10px_rgba(0,255,255,0.2)] focus-visible:ring-2 focus-visible:ring-neon-cyan"
                            autoFocus
                        />
                    </div>

                    {/* Language Grid */}
                    <div className="safe-area-scroll-panel grid max-h-[min(60dvh,28rem)] grid-cols-1 gap-2 overflow-y-auto pr-2 custom-scrollbar md:grid-cols-2">
                        {filteredLanguages.map((lang) => {
                            const isActive = lang.code === locale;
                            return (
                                <motion.button
                                    key={lang.code}
                                    onClick={() => handleLanguageChange(lang.code)}
                                    aria-label={`${lang.name} (${lang.nativeName})`}
                                    aria-pressed={isActive}
                                    layout
                                    className={`
                                        touch-target flex items-center gap-3 rounded border p-3 text-left relative overflow-hidden group
                                        transition-all duration-200
                                        focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]
                                        ${isActive
                                            ? 'bg-neon-cyan/10 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.15)]'
                                            : 'bg-terminal-surface/30 border-grid-line/10 hover:border-neon-pink/50 hover:bg-terminal-surface/60'
                                        }
                                    `}
                                >
                                    {/* Scanline effect on hover */}
                                    <div className="absolute inset-0 opacity-0 group-hover:opacity-10 pointer-events-none bg-gradient-to-b from-transparent via-white to-transparent -translate-y-full group-hover:translate-y-full transition-all duration-700 ease-linear" />

                                    <div className="filter drop-shadow-md flex-shrink-0">
                                        <CountryFlag
                                            code={lang.countryCode}
                                            className="rounded-[2px] w-7 h-auto" // w-7 is 28px
                                        />
                                    </div>

                                    <div className="flex flex-col min-w-0">
                                        <span className={`font-display text-sm tracking-wide truncate ${isActive ? 'text-neon-cyan' : 'text-foreground group-hover:text-neon-pink'}`}>
                                            {lang.name}
                                        </span>
                                        <span className="text-xs text-muted-foreground font-mono truncate">
                                            {lang.nativeName}
                                        </span>
                                    </div>

                                    {isActive && (
                                        <motion.div
                                            layoutId="active-check"
                                            className="ml-auto text-neon-cyan flex-shrink-0"
                                        >
                                            <Check size={18} />
                                        </motion.div>
                                    )}
                                </motion.button>
                            );
                        })}
                    </div>

                    {filteredLanguages.length === 0 && (
                        <div className="text-center py-8 text-muted-foreground font-mono">
                            {/* NO_MATCHES_FOUND */}
                            NO_MATCHES_FOUND
                        </div>
                    )}
                </div>
            </Modal>
        </>
    );
}
