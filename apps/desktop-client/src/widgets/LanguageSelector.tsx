import { useState, useRef, useEffect } from "react";
import { Globe, Check } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";
import { locales, localeNames, Locale } from "../shared/i18n/config";

export function LanguageSelector() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentLocale = (i18n.language || "en-EN") as Locale;

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
    <div className="relative inline-block text-left" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex justify-center items-center h-10 px-3 transition-colors cursor-pointer text-muted-foreground hover:text-white ${
          isOpen ? "bg-white/10 text-white" : "hover:bg-white/5"
        }`}
        title="Select Language"
      >
        <Globe size={14} className={isOpen ? "text-[var(--color-matrix-green)] drop-shadow-[0_0_8px_var(--color-matrix-green)]" : ""} />
        <span className="ml-2 text-xs font-mono hidden sm:inline-block">
          {localeNames[currentLocale] || currentLocale}
        </span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            style={{ 
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
            }}
            className="absolute right-0 mt-2 w-64 max-h-[60vh] overflow-y-auto overflow-x-hidden origin-top-right rounded-md border border-white/10 bg-black/80 shadow-2xl z-50 premium-scrollbar"
          >
            {/* Scramble-like accent header */}
            <div className="sticky top-0 bg-black/90 px-3 py-2 border-b border-white/5 flex items-center z-10">
               <span className="text-[10px] font-mono text-[var(--color-matrix-green)] uppercase tracking-widest opacity-80">
                 Select Region / Language
               </span>
            </div>

            <div className="p-1">
              {locales.map((code) => {
                const isSelected = code === currentLocale;
                return (
                  <button
                    key={code}
                    onClick={() => handleSelect(code as Locale)}
                    className={`w-full text-left flex items-center px-3 py-2 text-sm rounded-sm transition-all duration-150 ${
                      isSelected 
                        ? "bg-[var(--color-matrix-green)]/10 text-[var(--color-matrix-green)]" 
                        : "text-muted-foreground hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <span className="flex-1 font-mono text-xs">{localeNames[code as Locale]}</span>
                    {isSelected && (
                      <motion.div
                        layoutId="active-lang"
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
