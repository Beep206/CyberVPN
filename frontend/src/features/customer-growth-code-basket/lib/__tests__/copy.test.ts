import { describe, expect, it } from 'vitest';
import enMessages from '@/i18n/messages/generated/en-EN.json';
import ruMessages from '@/i18n/messages/generated/ru-RU.json';
import { buildGrowthCodeBasketCopy } from '../copy';

type MessageValue = string | { [key: string]: MessageValue };
type MessageBundle = {
  Subscriptions: { [key: string]: MessageValue };
};

function createSubscriptionsTranslator(messages: MessageBundle) {
  return (key: string, values?: Record<string, string | number | Date>) => {
    const value = key.split('.').reduce<MessageValue | undefined>((node, part) => {
      if (!node || typeof node === 'string') {
        return undefined;
      }

      return node[part];
    }, messages.Subscriptions);

    if (typeof value !== 'string') {
      throw new Error(`Missing test message: Subscriptions.${key}`);
    }

    return value.replace(/\{(\w+)\}/g, (match, name: string) => {
      const replacement = values?.[name];

      return replacement == null ? match : String(replacement);
    });
  };
}

describe('buildGrowthCodeBasketCopy', () => {
  it.each([
    {
      locale: 'en-EN',
      messages: enMessages,
      namespaceAmbiguous:
        'This code matches more than one code type. Use the right surface or contact support.',
    },
    {
      locale: 'ru-RU',
      messages: ruMessages,
      namespaceAmbiguous:
        'Этот код совпадает с несколькими типами. Используйте нужную поверхность или обратитесь в поддержку.',
    },
  ])('resolves all growth code basket messages for $locale', ({ messages, namespaceAmbiguous }) => {
    const copy = buildGrowthCodeBasketCopy(createSubscriptionsTranslator(messages));

    expect(copy.resolutionErrors.namespaceAmbiguous).toBe(namespaceAmbiguous);
  });
});
