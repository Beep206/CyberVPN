export const locales = [
  "en-EN", "ru-RU", "zh-CN", "hi-IN", "id-ID", "vi-VN", "th-TH",
  "ja-JP", "ko-KR", "ar-SA", "fa-IR", "tr-TR", "ur-PK", "bn-BD",
  "ms-MY", "es-ES", "kk-KZ", "be-BY", "my-MM", "uz-UZ", "ha-NG",
  "yo-NG", "ku-IQ", "am-ET", "fr-FR", "tk-TM", "he-IL", "de-DE",
  "pt-PT", "it-IT", "nl-NL", "pl-PL", "fil-PH", "uk-UA", "cs-CZ",
  "ro-RO", "hu-HU", "sv-SE",
] as const;

export type Locale = typeof locales[number];

type LocaleSeed = {
  code: Locale;
  name: string;
  nativeName: string;
  countryCode: string;
};

export type LocaleDescriptor = LocaleSeed & {
  flag: string;
  searchCode: string;
  searchName: string;
  searchNative: string;
};

function toFlagEmoji(countryCode: string) {
  const normalized = countryCode.trim().toUpperCase();

  if (!/^[A-Z]{2}$/.test(normalized)) {
    return "🌐";
  }

  return String.fromCodePoint(
    ...normalized.split("").map((char) => 0x1f1e6 + char.charCodeAt(0) - 65)
  );
}

const localeSeeds: readonly LocaleSeed[] = [
  { code: "en-EN", name: "English", nativeName: "English", countryCode: "US" },
  { code: "ru-RU", name: "Russian", nativeName: "Русский", countryCode: "RU" },
  { code: "zh-CN", name: "Chinese", nativeName: "中文", countryCode: "CN" },
  { code: "hi-IN", name: "Hindi", nativeName: "हिन्दी", countryCode: "IN" },
  { code: "id-ID", name: "Indonesian", nativeName: "Bahasa Indonesia", countryCode: "ID" },
  { code: "vi-VN", name: "Vietnamese", nativeName: "Tiếng Việt", countryCode: "VN" },
  { code: "th-TH", name: "Thai", nativeName: "ไทย", countryCode: "TH" },
  { code: "ja-JP", name: "Japanese", nativeName: "日本語", countryCode: "JP" },
  { code: "ko-KR", name: "Korean", nativeName: "한국어", countryCode: "KR" },
  { code: "ar-SA", name: "Arabic", nativeName: "العربية", countryCode: "SA" },
  { code: "fa-IR", name: "Persian", nativeName: "فارسی", countryCode: "IR" },
  { code: "tr-TR", name: "Turkish", nativeName: "Türkçe", countryCode: "TR" },
  { code: "ur-PK", name: "Urdu", nativeName: "اردو", countryCode: "PK" },
  { code: "bn-BD", name: "Bengali", nativeName: "বাংলা", countryCode: "BD" },
  { code: "ms-MY", name: "Malay", nativeName: "Bahasa Melayu", countryCode: "MY" },
  { code: "es-ES", name: "Spanish", nativeName: "Español", countryCode: "ES" },
  { code: "kk-KZ", name: "Kazakh", nativeName: "Қазақша", countryCode: "KZ" },
  { code: "be-BY", name: "Belarusian", nativeName: "Беларуская", countryCode: "BY" },
  { code: "my-MM", name: "Burmese", nativeName: "မြန်မာ", countryCode: "MM" },
  { code: "uz-UZ", name: "Uzbek", nativeName: "Oʻzbekcha", countryCode: "UZ" },
  { code: "ha-NG", name: "Hausa", nativeName: "Hausa", countryCode: "NG" },
  { code: "yo-NG", name: "Yoruba", nativeName: "Yorùbá", countryCode: "NG" },
  { code: "ku-IQ", name: "Kurdish", nativeName: "Kurdî", countryCode: "IQ" },
  { code: "am-ET", name: "Amharic", nativeName: "አማርኛ", countryCode: "ET" },
  { code: "fr-FR", name: "French", nativeName: "Français", countryCode: "FR" },
  { code: "tk-TM", name: "Turkmen", nativeName: "Türkmençe", countryCode: "TM" },
  { code: "he-IL", name: "Hebrew", nativeName: "עברית", countryCode: "IL" },
  { code: "de-DE", name: "German", nativeName: "Deutsch", countryCode: "DE" },
  { code: "pt-PT", name: "Portuguese", nativeName: "Português", countryCode: "PT" },
  { code: "it-IT", name: "Italian", nativeName: "Italiano", countryCode: "IT" },
  { code: "nl-NL", name: "Dutch", nativeName: "Nederlands", countryCode: "NL" },
  { code: "pl-PL", name: "Polish", nativeName: "Polski", countryCode: "PL" },
  { code: "fil-PH", name: "Filipino", nativeName: "Filipino", countryCode: "PH" },
  { code: "uk-UA", name: "Ukrainian", nativeName: "Українська", countryCode: "UA" },
  { code: "cs-CZ", name: "Czech", nativeName: "Čeština", countryCode: "CZ" },
  { code: "ro-RO", name: "Romanian", nativeName: "Română", countryCode: "RO" },
  { code: "hu-HU", name: "Hungarian", nativeName: "Magyar", countryCode: "HU" },
  { code: "sv-SE", name: "Swedish", nativeName: "Svenska", countryCode: "SE" },
];

export const localeCatalog: LocaleDescriptor[] = localeSeeds.map((entry) => ({
  ...entry,
  flag: toFlagEmoji(entry.countryCode),
  searchCode: entry.code.toLowerCase(),
  searchName: entry.name.toLowerCase(),
  searchNative: entry.nativeName.toLowerCase(),
}));

export const localeMeta = Object.fromEntries(
  localeCatalog.map((entry) => [entry.code, entry])
) as Record<Locale, LocaleDescriptor>;

export const localeNames = Object.fromEntries(
  localeCatalog.map((entry) => [entry.code, entry.nativeName])
) as Record<Locale, string>;

export const defaultLocale = "en-EN";
export const rtlLocales = ["ar-SA", "he-IL", "fa-IR", "ur-PK", "ku-IQ"] as const;
