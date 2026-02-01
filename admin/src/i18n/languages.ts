import { locales } from './config';

interface LanguageBase {
    code: typeof locales[number];
    name: string;
    nativeName: string;
    flag: string;
}

export interface Language extends LanguageBase {
    _searchName: string;
    _searchNative: string;
    _searchCode: string;
}

const LANGUAGES_RAW: LanguageBase[] = [
    // High Priority
    { code: 'en-EN', name: 'English', nativeName: 'English', flag: '🇺🇸' },
    { code: 'hi-IN', name: 'Hindi', nativeName: 'हिन्दी', flag: '🇮🇳' },
    { code: 'id-ID', name: 'Indonesian', nativeName: 'Bahasa Indonesia', flag: '🇮🇩' },
    { code: 'ru-RU', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺' },
    { code: 'zh-CN', name: 'Chinese', nativeName: '中文', flag: '🇨🇳' },

    // Medium Priority
    { code: 'ar-SA', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦' },
    { code: 'fa-IR', name: 'Persian', nativeName: 'فارسی', flag: '🇮🇷' },
    { code: 'tr-TR', name: 'Turkish', nativeName: 'Türkçe', flag: '🇹🇷' },
    { code: 'vi-VN', name: 'Vietnamese', nativeName: 'Tiếng Việt', flag: '🇻🇳' },
    { code: 'ur-PK', name: 'Urdu', nativeName: 'اردو', flag: '🇵🇰' },

    // Low Priority
    { code: 'th-TH', name: 'Thai', nativeName: 'ไทย', flag: '🇹🇭' },
    { code: 'bn-BD', name: 'Bengali', nativeName: 'বাংলা', flag: '🇧🇩' },
    { code: 'ms-MY', name: 'Malay', nativeName: 'Bahasa Melayu', flag: '🇲🇾' },
    { code: 'es-ES', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
    { code: 'kk-KZ', name: 'Kazakh', nativeName: 'Қазақ тілі', flag: '🇰🇿' },
    { code: 'be-BY', name: 'Belarusian', nativeName: 'Беларуская', flag: '🇧🇾' },
    { code: 'my-MM', name: 'Burmese', nativeName: 'မြန်မာစာ', flag: '🇲🇲' },
    { code: 'uz-UZ', name: 'Uzbek', nativeName: 'Oʻzbek', flag: '🇺🇿' },

    // Non-viable (but required)
    { code: 'ha-NG', name: 'Hausa', nativeName: 'Hausa', flag: '🇳🇬' },
    { code: 'yo-NG', name: 'Yoruba', nativeName: 'Yorùbá', flag: '🇳🇬' },
    { code: 'ku-IQ', name: 'Kurdish', nativeName: 'Kurdî', flag: '🇮🇶' },
    { code: 'am-ET', name: 'Amharic', nativeName: 'አማርኛ', flag: '🇪🇹' },
    { code: 'fr-FR', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
    { code: 'tk-TM', name: 'Turkmen', nativeName: 'Türkmençe', flag: '🇹🇲' },

    // Additional
    { code: 'ja-JP', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵' },
    { code: 'ko-KR', name: 'Korean', nativeName: '한국어', flag: '🇰🇷' },
    { code: 'he-IL', name: 'Hebrew', nativeName: 'עברית', flag: '🇮🇱' },
    { code: 'de-DE', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
    { code: 'pt-PT', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹' },
    { code: 'it-IT', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹' },
    { code: 'nl-NL', name: 'Dutch', nativeName: 'Nederlands', flag: '🇳🇱' },
    { code: 'pl-PL', name: 'Polish', nativeName: 'Polski', flag: '🇵🇱' },
    { code: 'fil-PH', name: 'Filipino', nativeName: 'Filipino', flag: '🇵🇭' },
    { code: 'uk-UA', name: 'Ukrainian', nativeName: 'Українська', flag: '🇺🇦' },
    { code: 'cs-CZ', name: 'Czech', nativeName: 'Čeština', flag: '🇨🇿' },
    { code: 'ro-RO', name: 'Romanian', nativeName: 'Română', flag: '🇷🇴' },
    { code: 'hu-HU', name: 'Hungarian', nativeName: 'Magyar', flag: '🇭🇺' },
    { code: 'sv-SE', name: 'Swedish', nativeName: 'Svenska', flag: '🇸🇪' },
];

export const LANGUAGES: Language[] = LANGUAGES_RAW.map(l => ({
    ...l,
    _searchName: l.name.toLowerCase(),
    _searchNative: l.nativeName.toLowerCase(),
    _searchCode: l.code.toLowerCase(),
}));
