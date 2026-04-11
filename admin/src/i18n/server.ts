import { cacheLife } from 'next/cache';
import { createTranslator } from 'use-intl/core';
import {
  getFormatter,
  getLocale,
  getMessages,
  getNow,
  getTimeZone,
  setRequestLocale,
} from 'next-intl/server';

type IntlMessages = Awaited<ReturnType<typeof getMessages>>;

async function getCachedMessagesForLocale(locale: string) {
  'use cache';
  cacheLife('hours');

  return getMessages({ locale });
}

function pickMessages(
  messages: IntlMessages,
  namespaces: readonly string[],
): Record<string, unknown> {
  return namespaces.reduce<Record<string, unknown>>((acc, namespace) => {
    if (namespace in messages) {
      acc[namespace] = messages[namespace as keyof IntlMessages];
    }

    return acc;
  }, {});
}

export async function getCachedTranslations(
  locale: string,
  namespace?: string,
) {
  const messages = await getCachedMessagesForLocale(locale);

  return createTranslator({
    locale,
    messages,
    namespace,
  });
}

export async function getScopedMessages(
  locale: string,
  namespaces: readonly string[],
) {
  const messages = await getCachedMessagesForLocale(locale);

  return pickMessages(messages, namespaces);
}

export {
  getFormatter,
  getLocale,
  getMessages,
  getNow,
  getTimeZone,
  setRequestLocale,
};
