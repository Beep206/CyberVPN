export const locales = [
    // Высокий приоритет
    'en-EN', 'hi-IN', 'id-ID', 'ru-RU', 'zh-CN',
    // Средний приоритет
    'ar-SA', 'fa-IR', 'tr-TR', 'vi-VN', 'ur-PK',
    // Низкий приоритет
    'th-TH', 'bn-BD', 'ms-MY', 'es-ES', 'kk-KZ', 'be-BY', 'my-MM', 'uz-UZ',
    // Нежизнеспособные (но требуются)
    'ha-NG', 'yo-NG', 'ku-IQ', 'am-ET', 'fr-FR', 'tk-TM',
    // Дополнительные
    'ja-JP', 'ko-KR', 'he-IL', 'de-DE', 'pt-PT', 'it-IT', 'nl-NL', 'pl-PL',
    'fil-PH', 'uk-UA', 'cs-CZ', 'ro-RO', 'hu-HU', 'sv-SE'
] as const;

export const defaultLocale = 'en-EN';

export const rtlLocales = ['ar-SA', 'he-IL', 'fa-IR', 'ur-PK', 'ku-IQ'] as const;
