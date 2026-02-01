'use client';

import { startTransition, useState } from 'react';
import { useLocale } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { motion } from 'motion/react';
import { Globe, Search, Check } from 'lucide-react';
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

    const query = searchQuery.toLowerCase();
    const filteredLanguages = LANGUAGES.filter(l =>
        l._searchName.includes(query) ||
        l._searchNative.includes(query) ||
        l._searchCode.includes(query)
    );

    const handleLanguageChange = (newLocale: string) => {
        router.replace(pathname, { locale: newLocale });
        setIsOpen(false);
    };

    return (
        <>
            <MagneticButton strength={20}>
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setIsOpen(true)}
                    className="flex h-10 items-center justify-center gap-2 px-3 rounded-lg bg-terminal-surface/30 border border-grid-line/30 text-muted-foreground hover:text-neon-cyan hover:border-neon-cyan/50 hover:bg-neon-cyan/10 transition-colors duration-300 group"
                >
                    <span className="text-xl filter drop-shadow-[0_0_2px_rgba(255,255,255,0.5)] leading-none">
                        {currentLanguage.flag}
                    </span>
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
                            className="w-full bg-terminal-bg/50 border border-grid-line/30 rounded-md py-2 pl-10 pr-4 text-foreground font-mono focus:outline-none focus:border-neon-cyan focus:shadow-[0_0_10px_rgba(0,255,255,0.2)] transition-all duration-300 placeholder:text-muted-foreground"
                            autoFocus
                        />
                    </div>

                    {/* Language Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {filteredLanguages.map((lang) => {
                            const isActive = lang.code === locale;
                            return (
                                <motion.button
                                    key={lang.code}
                                    onClick={() => handleLanguageChange(lang.code)}
                                    layout
                                    className={`
                                        flex items-center gap-3 p-3 rounded border text-left relative overflow-hidden group
                                        transition-all duration-200
                                        ${isActive
                                            ? 'bg-neon-cyan/10 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.15)]'
                                            : 'bg-terminal-surface/30 border-grid-line/10 hover:border-neon-pink/50 hover:bg-terminal-surface/60'
                                        }
                                    `}
                                >
                                    {/* Scanline effect on hover */}
                                    <div className="absolute inset-0 opacity-0 group-hover:opacity-10 pointer-events-none bg-gradient-to-b from-transparent via-white to-transparent -translate-y-full group-hover:translate-y-full transition-all duration-700 ease-linear" />

                                    <span className="text-2xl filter drop-shadow-md">
                                        {lang.flag}
                                    </span>

                                    <div className="flex flex-col">
                                        <span className={`font-display text-sm tracking-wide ${isActive ? 'text-neon-cyan' : 'text-foreground group-hover:text-neon-pink'}`}>
                                            {lang.name}
                                        </span>
                                        <span className="text-xs text-muted-foreground font-mono">
                                            {lang.nativeName}
                                        </span>
                                    </div>

                                    {isActive && (
                                        <motion.div
                                            layoutId="active-check"
                                            className="ml-auto text-neon-cyan"
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
                            // NO_MATCHES_FOUND
                        </div>
                    )}
                </div>
            </Modal>
        </>
    );
}
