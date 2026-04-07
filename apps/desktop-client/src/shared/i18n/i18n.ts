import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { defaultLocale, locales } from './config';
import { invoke } from '@tauri-apps/api/core';

// Static JSON imports — zero network overhead, fully bundled
import enTranslation from './locales/en-EN.json';
import ruTranslation from './locales/ru-RU.json';

// ─── TypeScript Type Safety ────────────────────────────────────────────────
// All translation keys are inferred from the authoritative en-EN source.
// This enables autocomplete and compile-time key validation via react-i18next.
declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'translation';
    resources: {
      translation: typeof enTranslation;
    };
  }
}
// ──────────────────────────────────────────────────────────────────────────

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    // Locale resolution
    fallbackLng: defaultLocale,
    supportedLngs: locales,
    load: 'currentOnly',

    // Parser config
    interpolation: {
      escapeValue: false, // React handles XSS escaping natively
    },

    // Flat single-namespace architecture — all keys under `translation`
    defaultNS: 'translation',

    // Robustness: return key instead of null for missing translations
    returnNull: false,
    returnEmptyString: false,

    // Language Detector priority: Tauri store → localStorage → navigator
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },

    // Static resource bundle — loaded at init, never fetched over http
    resources: {
      'en-EN': { translation: enTranslation },
      'ru-RU': { translation: ruTranslation },
    },
  });

// ─── Rust Bridge ──────────────────────────────────────────────────────────
// When locale changes in the React side, synchronize with Tauri backend
// so tray menu, system notifications, and Rust-generated strings match.
i18n.on('languageChanged', (lng) => {
  invoke('set_app_locale', { locale: lng }).catch((e) => {
    console.warn('[i18n] Failed to sync locale to Rust backend:', e);
  });
});
// ──────────────────────────────────────────────────────────────────────────

export default i18n;
