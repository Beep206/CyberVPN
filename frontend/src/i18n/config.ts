export const highPriorityLocales = [
  'en-EN',
  'ru-RU',
  'zh-CN',
  'hi-IN',
  'id-ID',
  'vi-VN',
  'th-TH',
  'ja-JP',
  'ko-KR',
] as const;

export const mediumPriorityLocales = [
  'ar-SA',
  'fa-IR',
  'tr-TR',
  'ur-PK',
] as const;

export const lowPriorityLocales = [
  'bn-BD',
  'ms-MY',
  'es-ES',
  'kk-KZ',
  'be-BY',
  'my-MM',
  'uz-UZ',
] as const;

export const requiredFallbackLocales = [
  'ha-NG',
  'yo-NG',
  'ku-IQ',
  'am-ET',
  'fr-FR',
  'tk-TM',
] as const;

export const additionalLocales = [
  'he-IL',
  'de-DE',
  'pt-PT',
  'it-IT',
  'nl-NL',
  'pl-PL',
  'fil-PH',
  'uk-UA',
  'cs-CZ',
  'ro-RO',
  'hu-HU',
  'sv-SE',
] as const;

export const locales = [
  ...highPriorityLocales,
  ...mediumPriorityLocales,
  ...lowPriorityLocales,
  ...requiredFallbackLocales,
  ...additionalLocales,
] as const;

export const defaultLocale = 'en-EN';

export const rtlLocales = ['ar-SA', 'he-IL', 'fa-IR', 'ur-PK', 'ku-IQ'] as const;

export function getStaticParamsLocales(): readonly string[] {
  return process.env.NODE_ENV === 'development' ? [defaultLocale] : locales;
}
