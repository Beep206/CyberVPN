import { useState, useRef, useEffect } from "react";
import { Check, Globe2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { localeCatalog, localeMeta, Locale } from "../shared/i18n/config";
import { desktopMotionEase, useDesktopMotionBudget } from "../shared/lib/motion";
import { CountryFlag } from "../shared/ui/country-flag";

export function LanguageSelector() {
  const { i18n } = useTranslation();
  const { prefersReducedMotion, durations } = useDesktopMotionBudget();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentLocale = (i18n.language || "en-EN") as Locale;
  const currentLocaleEntry = localeMeta[currentLocale] ?? localeCatalog[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (code: Locale) => {
    i18n.changeLanguage(code);
    setIsOpen(false);
  };

  return (
    <div data-tauri-drag-region="false" className="relative inline-block text-left" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex h-9 cursor-pointer items-center justify-center rounded-full px-3 text-muted-foreground transition-colors hover:text-foreground ${
          isOpen ? "bg-accent/80 text-foreground" : "hover:bg-accent/60"
        }`}
        title="Select Language"
      >
        <span aria-hidden className="flex h-5 w-6 items-center justify-center">
          <CountryFlag
            code={currentLocaleEntry.countryCode}
            className="h-4 w-6 rounded-[0.2rem] shadow-[var(--panel-shadow)]"
            fallbackClassName="h-4 w-6"
          />
        </span>
        <span className="ml-2 hidden min-w-0 flex-col text-left sm:flex">
          <span className="truncate text-[11px] font-semibold tracking-[0.08em] text-foreground">
            {currentLocaleEntry.nativeName}
          </span>
        </span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: prefersReducedMotion ? 0 : -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -4 }}
            transition={{ duration: durations.micro, ease: desktopMotionEase }}
            style={{
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
            }}
            className="premium-scrollbar absolute right-0 z-50 mt-2 max-h-[70vh] w-[min(40rem,calc(100vw-1.5rem))] origin-top-right overflow-x-hidden overflow-y-auto rounded-3xl border border-border/70 bg-[color:var(--chrome-elevated)]/96 shadow-[var(--panel-shadow-strong)] dark:shadow-black/40"
          >
            <div className="sticky top-0 z-10 flex items-center border-b border-border/70 bg-[color:var(--chrome-surface)]/92 px-4 py-3">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-[color:color-mix(in_oklab,var(--color-matrix-green)_24%,var(--border))] bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-[var(--color-matrix-green)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_14%,black)]">
                <Globe2 size={14} />
              </div>
              <span className="ml-3 text-[10px] font-mono text-[var(--color-matrix-green)] uppercase tracking-[0.22em] opacity-80">
                Select Region / Language
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 p-2">
              {localeCatalog.map((entry) => {
                const code = entry.code;
                const isSelected = code === currentLocale;

                return (
                  <button
                    key={code}
                    onClick={() => handleSelect(code)}
                    className={`relative flex min-h-[4.5rem] w-full items-start gap-3 rounded-2xl px-3 py-3 text-left text-sm transition-colors duration-150 ${
                      isSelected 
                        ? "bg-[color:color-mix(in_oklab,var(--color-matrix-green)_10%,white)] text-foreground ring-1 ring-[color:color-mix(in_oklab,var(--color-matrix-green)_26%,var(--border))] shadow-[var(--panel-shadow)] dark:bg-[color:color-mix(in_oklab,var(--color-matrix-green)_18%,black)] dark:text-[var(--color-matrix-green)] dark:ring-[color:color-mix(in_oklab,var(--color-matrix-green)_38%,var(--border))] dark:shadow-[0_12px_28px_rgba(56,240,160,0.16)]"
                        : "text-muted-foreground hover:bg-accent/70 hover:text-foreground"
                    }`}
                  >
                    <span aria-hidden className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center">
                      <CountryFlag
                        code={entry.countryCode}
                        className="h-5 w-8 rounded-[0.25rem] border border-border/65 shadow-[var(--panel-shadow)]"
                        fallbackClassName="h-5 w-8"
                      />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-foreground">
                        {entry.name}
                      </span>
                      <span className="mt-1 block truncate text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                        {entry.nativeName}
                      </span>
                    </span>
                    {isSelected && (
                      <motion.div
                        layoutId="active-lang"
                        className="mt-1 shrink-0"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                      >
                        <Check size={14} />
                      </motion.div>
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
