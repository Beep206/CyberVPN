export const locales = [
  'en-EN', 'ru-RU', 'zh-CN', 'hi-IN', 'id-ID', 'vi-VN', 'th-TH',
  'ja-JP', 'ko-KR', 'ar-SA', 'fa-IR', 'tr-TR', 'ur-PK', 'bn-BD',
  'ms-MY', 'es-ES', 'kk-KZ', 'be-BY', 'my-MM', 'uz-UZ', 'ha-NG',
  'yo-NG', 'ku-IQ', 'am-ET', 'fr-FR', 'tk-TM', 'he-IL', 'de-DE',
  'pt-PT', 'it-IT', 'nl-NL', 'pl-PL', 'fil-PH', 'uk-UA', 'cs-CZ',
  'ro-RO', 'hu-HU', 'sv-SE'
] as const;

export type Locale = typeof locales[number];

export const localeNames: Record<Locale, string> = {
  'en-EN': 'English',
  'ru-RU': 'Русский',
  'zh-CN': '中文',
  'hi-IN': 'हिन्दी',
  'id-ID': 'Bahasa Indonesia',
  'vi-VN': 'Tiếng Việt',
  'th-TH': 'ไทย',
  'ja-JP': '日本語',
  'ko-KR': '한국어',
  'ar-SA': 'العربية',
  'fa-IR': 'فارسی',
  'tr-TR': 'Türkçe',
  'ur-PK': 'اردو',
  'bn-BD': 'বাংলা',
  'ms-MY': 'Bahasa Melayu',
  'es-ES': 'Español',
  'kk-KZ': 'Қазақша',
  'be-BY': 'Беларуская',
  'my-MM': 'မြန်မာ',
  'uz-UZ': 'Oʻzbekcha',
  'ha-NG': 'Hausa',
  'yo-NG': 'Yorùbá',
  'ku-IQ': 'Kurdî',
  'am-ET': 'አማርኛ',
  'fr-FR': 'Français',
  'tk-TM': 'Türkmençe',
  'he-IL': 'עברית',
  'de-DE': 'Deutsch',
  'pt-PT': 'Português',
  'it-IT': 'Italiano',
  'nl-NL': 'Nederlands',
  'pl-PL': 'Polski',
  'fil-PH': 'Filipino',
  'uk-UA': 'Українська',
  'cs-CZ': 'Čeština',
  'ro-RO': 'Română',
  'hu-HU': 'Magyar',
  'sv-SE': 'Svenska'
};

export const defaultLocale = 'en-EN';
export const rtlLocales = ['ar-SA', 'he-IL', 'fa-IR', 'ur-PK', 'ku-IQ'] as const;
