import { locales } from './config';

interface LanguageBase {
    code: typeof locales[number];
    name: string;
    nativeName: string;
    flag: string;
    countryCode: string;
}

export interface Language extends LanguageBase {
    _searchName: string;
    _searchNative: string;
    _searchCode: string;
}

const LANGUAGES_RAW: LanguageBase[] = [
    // High Priority
    { code: 'en-EN', name: 'English', nativeName: 'English', flag: '🇺🇸', countryCode: 'US' },
    { code: 'hi-IN', name: 'Hindi', nativeName: 'हिन्दी', flag: '🇮🇳', countryCode: 'IN' },
    { code: 'id-ID', name: 'Indonesian', nativeName: 'Bahasa Indonesia', flag: '🇮🇩', countryCode: 'ID' },
    { code: 'ru-RU', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺', countryCode: 'RU' },
    { code: 'zh-CN', name: 'Chinese', nativeName: '中文', flag: '🇨🇳', countryCode: 'CN' },

    // Medium Priority
    { code: 'ar-SA', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦', countryCode: 'SA' },
    { code: 'fa-IR', name: 'Persian', nativeName: 'فارسی', flag: '🇮🇷', countryCode: 'IR' },
    { code: 'tr-TR', name: 'Turkish', nativeName: 'Türkçe', flag: '🇹🇷', countryCode: 'TR' },
    { code: 'vi-VN', name: 'Vietnamese', nativeName: 'Tiếng Việt', flag: '🇻🇳', countryCode: 'VN' },
    { code: 'ur-PK', name: 'Urdu', nativeName: 'اردو', flag: '🇵🇰', countryCode: 'PK' },

    // Low Priority
    { code: 'th-TH', name: 'Thai', nativeName: 'ไทย', flag: '🇹🇭', countryCode: 'TH' },
    { code: 'bn-BD', name: 'Bengali', nativeName: 'বাংলা', flag: '🇧🇩', countryCode: 'BD' },
    { code: 'ms-MY', name: 'Malay', nativeName: 'Bahasa Melayu', flag: '🇲🇾', countryCode: 'MY' },
    { code: 'es-ES', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸', countryCode: 'ES' },
    { code: 'kk-KZ', name: 'Kazakh', nativeName: 'Қазақ тілі', flag: '🇰🇿', countryCode: 'KZ' },
    { code: 'be-BY', name: 'Belarusian', nativeName: 'Беларуская', flag: '🇧🇾', countryCode: 'BY' },
    { code: 'my-MM', name: 'Burmese', nativeName: 'မြန်မာစာ', flag: '🇲🇲', countryCode: 'MM' },
    { code: 'uz-UZ', name: 'Uzbek', nativeName: 'Oʻzbek', flag: '🇺🇿', countryCode: 'UZ' },

    // Non-viable (but required)
    { code: 'ha-NG', name: 'Hausa', nativeName: 'Hausa', flag: '🇳🇬', countryCode: 'NG' },
    { code: 'yo-NG', name: 'Yoruba', nativeName: 'Yorùbá', flag: '🇳🇬', countryCode: 'NG' },
    { code: 'ku-IQ', name: 'Kurdish', nativeName: 'Kurdî', flag: '🇮🇶', countryCode: 'IQ' },
    { code: 'am-ET', name: 'Amharic', nativeName: 'አማርኛ', flag: '🇪🇹', countryCode: 'ET' },
    { code: 'fr-FR', name: 'French', nativeName: 'Français', flag: '🇫🇷', countryCode: 'FR' },
    { code: 'tk-TM', name: 'Turkmen', nativeName: 'Türkmençe', flag: '🇹🇲', countryCode: 'TM' },

    // Additional
    { code: 'ja-JP', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵', countryCode: 'JP' },
    { code: 'ko-KR', name: 'Korean', nativeName: '한국어', flag: '🇰🇷', countryCode: 'KR' },
    { code: 'he-IL', name: 'Hebrew', nativeName: 'עברית', flag: '🇮🇱', countryCode: 'IL' },
    { code: 'de-DE', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪', countryCode: 'DE' },
    { code: 'pt-PT', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹', countryCode: 'PT' },
    { code: 'it-IT', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹', countryCode: 'IT' },
    { code: 'nl-NL', name: 'Dutch', nativeName: 'Nederlands', flag: '🇳🇱', countryCode: 'NL' },
    { code: 'pl-PL', name: 'Polish', nativeName: 'Polski', flag: '🇵🇱', countryCode: 'PL' },
    { code: 'fil-PH', name: 'Filipino', nativeName: 'Filipino', flag: '🇵🇭', countryCode: 'PH' },
    { code: 'uk-UA', name: 'Ukrainian', nativeName: 'Українська', flag: '🇺🇦', countryCode: 'UA' },
    { code: 'cs-CZ', name: 'Czech', nativeName: 'Čeština', flag: '🇨🇿', countryCode: 'CZ' },
    { code: 'ro-RO', name: 'Romanian', nativeName: 'Română', flag: '🇷🇴', countryCode: 'RO' },
    { code: 'hu-HU', name: 'Hungarian', nativeName: 'Magyar', flag: '🇭🇺', countryCode: 'HU' },
    { code: 'sv-SE', name: 'Swedish', nativeName: 'Svenska', flag: '🇸🇪', countryCode: 'SE' },
];

export const LANGUAGES: Language[] = LANGUAGES_RAW.map(l => ({
    ...l,
    _searchName: l.name.toLowerCase(),
    _searchNative: l.nativeName.toLowerCase(),
    _searchCode: l.code.toLowerCase(),
}));
