import { type locales } from './config';

type Locale = (typeof locales)[number];
type Messages = Record<string, unknown>;
type LocaleMessagesLoader = () => Promise<Messages>;

const localeMessagesLoaders = {
  'ru-RU': () => import('./messages/generated/ru-RU.json').then((module) => module.default as Messages),
  'en-EN': () => import('./messages/generated/en-EN.json').then((module) => module.default as Messages),
} satisfies Record<Locale, LocaleMessagesLoader>;

export async function loadCompiledLocaleMessages(locale: Locale) {
  return localeMessagesLoaders[locale]();
}
