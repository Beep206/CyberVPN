export const highPriorityLocales = [
  'ru-RU',
  'en-EN',
] as const;

export const mediumPriorityLocales = [] as const;

export const lowPriorityLocales = [] as const;

export const requiredFallbackLocales = [] as const;

export const additionalLocales = [] as const;

export const locales = [
  ...highPriorityLocales,
  ...mediumPriorityLocales,
  ...lowPriorityLocales,
  ...requiredFallbackLocales,
  ...additionalLocales,
] as const;

export const defaultLocale = 'ru-RU';

export const rtlLocales = [] as const;

export function getStaticParamsLocales(): readonly string[] {
  return locales;
}
