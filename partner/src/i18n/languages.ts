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
    { code: 'ru-RU', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺', countryCode: 'RU' },
    { code: 'en-EN', name: 'English', nativeName: 'English', flag: '🇺🇸', countryCode: 'US' },
];

export const LANGUAGES: Language[] = LANGUAGES_RAW.map(l => ({
    ...l,
    _searchName: l.name.toLowerCase(),
    _searchNative: l.nativeName.toLowerCase(),
    _searchCode: l.code.toLowerCase(),
}));
