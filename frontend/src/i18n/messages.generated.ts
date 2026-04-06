import { type locales } from './config';

type Locale = (typeof locales)[number];
type Messages = Record<string, unknown>;
type LocaleMessagesLoader = () => Promise<Messages>;

const localeMessagesLoaders = {
  'am-ET': () => import('./messages/generated/am-ET.json').then((module) => module.default as Messages),
  'ar-SA': () => import('./messages/generated/ar-SA.json').then((module) => module.default as Messages),
  'be-BY': () => import('./messages/generated/be-BY.json').then((module) => module.default as Messages),
  'bn-BD': () => import('./messages/generated/bn-BD.json').then((module) => module.default as Messages),
  'cs-CZ': () => import('./messages/generated/cs-CZ.json').then((module) => module.default as Messages),
  'de-DE': () => import('./messages/generated/de-DE.json').then((module) => module.default as Messages),
  'en-EN': () => import('./messages/generated/en-EN.json').then((module) => module.default as Messages),
  'es-ES': () => import('./messages/generated/es-ES.json').then((module) => module.default as Messages),
  'fa-IR': () => import('./messages/generated/fa-IR.json').then((module) => module.default as Messages),
  'fil-PH': () => import('./messages/generated/fil-PH.json').then((module) => module.default as Messages),
  'fr-FR': () => import('./messages/generated/fr-FR.json').then((module) => module.default as Messages),
  'ha-NG': () => import('./messages/generated/ha-NG.json').then((module) => module.default as Messages),
  'he-IL': () => import('./messages/generated/he-IL.json').then((module) => module.default as Messages),
  'hi-IN': () => import('./messages/generated/hi-IN.json').then((module) => module.default as Messages),
  'hu-HU': () => import('./messages/generated/hu-HU.json').then((module) => module.default as Messages),
  'id-ID': () => import('./messages/generated/id-ID.json').then((module) => module.default as Messages),
  'it-IT': () => import('./messages/generated/it-IT.json').then((module) => module.default as Messages),
  'ja-JP': () => import('./messages/generated/ja-JP.json').then((module) => module.default as Messages),
  'kk-KZ': () => import('./messages/generated/kk-KZ.json').then((module) => module.default as Messages),
  'ko-KR': () => import('./messages/generated/ko-KR.json').then((module) => module.default as Messages),
  'ku-IQ': () => import('./messages/generated/ku-IQ.json').then((module) => module.default as Messages),
  'ms-MY': () => import('./messages/generated/ms-MY.json').then((module) => module.default as Messages),
  'my-MM': () => import('./messages/generated/my-MM.json').then((module) => module.default as Messages),
  'nl-NL': () => import('./messages/generated/nl-NL.json').then((module) => module.default as Messages),
  'pl-PL': () => import('./messages/generated/pl-PL.json').then((module) => module.default as Messages),
  'pt-PT': () => import('./messages/generated/pt-PT.json').then((module) => module.default as Messages),
  'ro-RO': () => import('./messages/generated/ro-RO.json').then((module) => module.default as Messages),
  'ru-RU': () => import('./messages/generated/ru-RU.json').then((module) => module.default as Messages),
  'sv-SE': () => import('./messages/generated/sv-SE.json').then((module) => module.default as Messages),
  'th-TH': () => import('./messages/generated/th-TH.json').then((module) => module.default as Messages),
  'tk-TM': () => import('./messages/generated/tk-TM.json').then((module) => module.default as Messages),
  'tr-TR': () => import('./messages/generated/tr-TR.json').then((module) => module.default as Messages),
  'uk-UA': () => import('./messages/generated/uk-UA.json').then((module) => module.default as Messages),
  'ur-PK': () => import('./messages/generated/ur-PK.json').then((module) => module.default as Messages),
  'uz-UZ': () => import('./messages/generated/uz-UZ.json').then((module) => module.default as Messages),
  'vi-VN': () => import('./messages/generated/vi-VN.json').then((module) => module.default as Messages),
  'yo-NG': () => import('./messages/generated/yo-NG.json').then((module) => module.default as Messages),
  'zh-CN': () => import('./messages/generated/zh-CN.json').then((module) => module.default as Messages),
  'zh-Hant': () => import('./messages/generated/zh-Hant.json').then((module) => module.default as Messages),
} satisfies Record<Locale, LocaleMessagesLoader>;

export async function loadCompiledLocaleMessages(locale: Locale) {
  return localeMessagesLoaders[locale]();
}
