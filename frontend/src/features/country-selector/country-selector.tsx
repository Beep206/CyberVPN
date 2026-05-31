'use client';

import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Check, Globe2, Search } from 'lucide-react';
import { motion } from 'motion/react';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { Modal } from '@/shared/ui/modal';
import { CountryFlag } from '@/shared/ui/country-flag';
import { normalizeCountryCode } from './country-config';
import { useCountryPreference } from './use-country-preference';

interface CountrySelectorProps {
  countries: string[];
  defaultCountry: string;
  onCountryChange?: (country: string) => void;
}

function getCountryDisplayName(locale: string, country: string) {
  try {
    return new Intl.DisplayNames([locale], { type: 'region' }).of(country) ?? country;
  } catch {
    return country;
  }
}

export function CountrySelector({
  countries,
  defaultCountry,
  onCountryChange,
}: CountrySelectorProps) {
  const locale = useLocale();
  const t = useTranslations('Pricing');
  const { country, setCountry } = useCountryPreference(defaultCountry);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const selectableCountries = Array.from(
    new Set(
      countries
        .map(normalizeCountryCode)
        .filter((code): code is string => Boolean(code)),
    ),
  );
  const query = searchQuery.trim().toLowerCase();
  const matchingCountries = selectableCountries.filter((code) =>
    `${code} ${getCountryDisplayName(locale, code)}`.toLowerCase().includes(query),
  );

  function handleSelect(nextCountry: string) {
    setCountry(nextCountry);
    setIsOpen(false);
    onCountryChange?.(nextCountry);
  }

  return (
    <>
      <MagneticButton strength={16}>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsOpen(true)}
          aria-label={`${t('countrySelector.aria')}: ${country}`}
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          className="touch-target inline-flex items-center justify-center gap-2 rounded-lg border border-grid-line/30 bg-terminal-surface/30 px-3 font-mono text-sm font-semibold uppercase tracking-wider text-muted-foreground transition-colors duration-300 hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
        >
          <Globe2 className="h-4 w-4" />
          {country}
        </motion.button>
      </MagneticButton>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={t('countrySelector.title')}
      >
        <div className="flex flex-col gap-4">
          <div className="group relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-grid-line transition-colors group-focus-within:text-neon-cyan" size={18} />
            <input
              type="text"
              placeholder={t('countrySelector.search')}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              aria-label={t('countrySelector.searchAria')}
              inputMode="search"
              spellCheck={false}
              className="mobile-form-input touch-target w-full rounded-md border border-grid-line/30 bg-terminal-bg/50 py-2 pl-10 pr-4 font-mono text-foreground transition-all duration-300 placeholder:text-muted-foreground focus-visible:border-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
              autoFocus
            />
          </div>

          <div className="safe-area-scroll-panel grid max-h-[min(60dvh,28rem)] grid-cols-1 gap-2 overflow-y-auto pr-2 custom-scrollbar md:grid-cols-2">
            {matchingCountries.map((code) => {
              const isActive = code === country;
              const countryName = getCountryDisplayName(locale, code);
              return (
                <motion.button
                  key={code}
                  onClick={() => handleSelect(code)}
                  aria-label={`${code} ${countryName}`}
                  aria-pressed={isActive}
                  layout
                  className={`touch-target relative flex items-center gap-3 overflow-hidden rounded border p-3 text-left transition-all duration-200 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan ${
                    isActive
                      ? 'border-neon-cyan bg-neon-cyan/10 shadow-[0_0_15px_rgba(0,255,255,0.15)]'
                      : 'border-grid-line/10 bg-terminal-surface/30 hover:border-neon-pink/50 hover:bg-terminal-surface/60'
                  }`}
                >
                  <CountryFlag code={code} className="h-auto w-7 rounded-[2px]" />
                  <div className="flex min-w-0 flex-col">
                    <span className={`truncate font-display text-sm tracking-wide ${isActive ? 'text-neon-cyan' : 'text-foreground'}`}>
                      {countryName}
                    </span>
                    <span className="truncate font-mono text-xs text-muted-foreground">
                      {code}
                    </span>
                  </div>
                  {isActive ? <Check className="ml-auto h-4 w-4 shrink-0 text-neon-cyan" /> : null}
                </motion.button>
              );
            })}
          </div>

          {matchingCountries.length === 0 ? (
            <div className="py-8 text-center font-mono text-muted-foreground">
              {t('countrySelector.empty')}
            </div>
          ) : null}
        </div>
      </Modal>
    </>
  );
}
