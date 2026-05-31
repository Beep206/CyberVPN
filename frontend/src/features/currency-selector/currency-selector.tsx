'use client';

import { useState } from 'react';
import { useLocale } from 'next-intl';
import { Check, Coins, Search } from 'lucide-react';
import { motion } from 'motion/react';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { Modal } from '@/shared/ui/modal';
import {
  CURRENCY_LABELS,
  SUPPORTED_CURRENCIES,
  isSupportedCurrency,
  type SupportedCurrency,
} from './currency-config';
import { useCurrencyPreference } from './use-currency-preference';

function copyForLocale(locale: string) {
  if (locale.startsWith('ru')) {
    return {
      aria: 'Выбрать валюту',
      empty: 'Валюта не найдена',
      search: 'ПОИСК_ВАЛЮТЫ...',
      title: 'SELECT_CURRENCY',
    };
  }

  return {
    aria: 'Select currency',
    empty: 'No currency found',
    search: 'SEARCH_CURRENCY...',
    title: 'SELECT_CURRENCY',
  };
}

function getCurrencySearchText(currency: SupportedCurrency) {
  return `${currency} ${CURRENCY_LABELS[currency]}`.toLowerCase();
}

interface CurrencySelectorProps {
  availableCurrencies?: readonly string[];
  defaultCurrency?: SupportedCurrency;
  onCurrencyChange?: (currency: SupportedCurrency) => void;
}

export function CurrencySelector({
  availableCurrencies,
  defaultCurrency,
  onCurrencyChange,
}: CurrencySelectorProps = {}) {
  const locale = useLocale();
  const copy = copyForLocale(locale);
  const { currency, setCurrency } = useCurrencyPreference(locale, defaultCurrency);
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const supportedCurrencies = availableCurrencies
    ? availableCurrencies.filter(isSupportedCurrency)
    : SUPPORTED_CURRENCIES;
  const query = searchQuery.trim().toLowerCase();
  const currencies = supportedCurrencies.filter((code) =>
    getCurrencySearchText(code).includes(query),
  );

  function handleSelect(nextCurrency: SupportedCurrency) {
    setCurrency(nextCurrency);
    setIsOpen(false);
    onCurrencyChange?.(nextCurrency);
  }

  return (
    <>
      <MagneticButton strength={16}>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsOpen(true)}
          aria-label={`${copy.aria}: ${currency}`}
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          className="touch-target inline-flex items-center justify-center gap-2 rounded-lg border border-grid-line/30 bg-terminal-surface/30 px-3 font-mono text-sm font-semibold uppercase tracking-wider text-muted-foreground transition-colors duration-300 hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
        >
          <Coins className="h-4 w-4" />
          {currency}
        </motion.button>
      </MagneticButton>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={copy.title}
      >
        <div className="flex flex-col gap-4">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-grid-line transition-colors group-focus-within:text-neon-cyan" size={18} />
            <input
              type="text"
              placeholder={copy.search}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              aria-label={copy.aria}
              inputMode="search"
              spellCheck={false}
              className="mobile-form-input touch-target w-full rounded-md border border-grid-line/30 bg-terminal-bg/50 py-2 pl-10 pr-4 font-mono text-foreground transition-all duration-300 placeholder:text-muted-foreground focus-visible:border-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
              autoFocus
            />
          </div>

          <div className="safe-area-scroll-panel grid max-h-[min(60dvh,28rem)] grid-cols-1 gap-2 overflow-y-auto pr-2 custom-scrollbar md:grid-cols-2">
            {currencies.map((code) => {
              const isActive = code === currency;
              return (
                <motion.button
                  key={code}
                  onClick={() => handleSelect(code)}
                  aria-label={`${code} ${CURRENCY_LABELS[code]}`}
                  aria-pressed={isActive}
                  layout
                  className={`touch-target relative flex items-center gap-3 overflow-hidden rounded border p-3 text-left transition-all duration-200 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan ${
                    isActive
                      ? 'border-neon-cyan bg-neon-cyan/10 shadow-[0_0_15px_rgba(0,255,255,0.15)]'
                      : 'border-grid-line/10 bg-terminal-surface/30 hover:border-neon-pink/50 hover:bg-terminal-surface/60'
                  }`}
                >
                  <div className="flex h-9 w-12 shrink-0 items-center justify-center rounded border border-grid-line/20 bg-background/55 font-mono text-xs font-bold text-foreground">
                    {code}
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <span className={`truncate font-display text-sm tracking-wide ${isActive ? 'text-neon-cyan' : 'text-foreground'}`}>
                      {code}
                    </span>
                    <span className="truncate font-mono text-xs text-muted-foreground">
                      {CURRENCY_LABELS[code]}
                    </span>
                  </div>
                  {isActive ? <Check className="ml-auto h-4 w-4 shrink-0 text-neon-cyan" /> : null}
                </motion.button>
              );
            })}
          </div>

          {currencies.length === 0 ? (
            <div className="py-8 text-center font-mono text-muted-foreground">
              {copy.empty}
            </div>
          ) : null}
        </div>
      </Modal>
    </>
  );
}
