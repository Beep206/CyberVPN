import { cache } from 'react';
import { getRequestConfig } from 'next-intl/server';
import { defaultLocale, locales } from './config';
import { loadCompiledLocaleMessages } from './messages.generated';

type Locale = (typeof locales)[number];
type Messages = Record<string, unknown>;
type RequestLocale = Promise<string | undefined> | string | undefined;

function deepMerge(target: Messages, source: Messages): Messages {
  const output = { ...target };

  for (const key in source) {
    if (
      Object.prototype.hasOwnProperty.call(source, key) &&
      source[key] != null &&
      typeof source[key] === 'object' &&
      !Array.isArray(source[key]) &&
      key in target &&
      target[key] != null &&
      typeof target[key] === 'object' &&
      !Array.isArray(target[key])
    ) {
      output[key] = deepMerge(target[key] as Messages, source[key] as Messages);
    } else {
      output[key] = source[key];
    }
  }

  return output;
}

const loadLocaleMessages = cache(async (locale: Locale) => loadCompiledLocaleMessages(locale));

export default getRequestConfig(async ({ requestLocale }) => {
  const resolvedLocale = await resolveRequestLocale(requestLocale);

  const baseMessages = await loadLocaleMessages(defaultLocale);
  let messages = baseMessages;

  if (resolvedLocale !== defaultLocale) {
    try {
      const currentMessages = await loadLocaleMessages(resolvedLocale);
      messages = deepMerge(baseMessages, currentMessages) as typeof baseMessages;
    } catch (error) {
      console.error(
        `Failed to load messages for ${resolvedLocale}, falling back to ${defaultLocale}`,
        error,
      );
    }
  }

  return {
    locale: resolvedLocale,
    messages,
  };
});

export async function resolveRequestLocale(requestLocale: RequestLocale): Promise<Locale> {
  const requestedLocale = await requestLocale;

  return locales.includes(requestedLocale as Locale)
    ? (requestedLocale as Locale)
    : defaultLocale;
}
