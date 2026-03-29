import { NextIntlClientProvider } from 'next-intl';
import { cacheLife } from 'next/cache';
import { getMessages } from 'next-intl/server';

type IntlMessages = Awaited<ReturnType<typeof getMessages>>;

async function getScopedMessages(
  locale: string,
  namespaces: readonly string[],
) {
  'use cache';
  cacheLife('hours');

  const messages = await getMessages({ locale });

  return pickMessages(messages, namespaces);
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

interface ScopedIntlProviderProps {
  children: React.ReactNode;
  locale: string;
  namespaces: readonly string[];
}

export async function ScopedIntlProvider({
  children,
  locale,
  namespaces,
}: ScopedIntlProviderProps) {
  const messages = await getScopedMessages(locale, namespaces);

  return <NextIntlClientProvider locale={locale} messages={messages}>{children}</NextIntlClientProvider>;
}
