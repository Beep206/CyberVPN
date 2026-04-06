import { NextIntlClientProvider } from 'next-intl';
import { getScopedMessages } from '@/i18n/server';

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

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
