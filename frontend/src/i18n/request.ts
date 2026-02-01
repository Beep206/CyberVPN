import { cache } from 'react';
import { getRequestConfig } from 'next-intl/server';
import { defaultLocale, locales } from './config';

type Locale = (typeof locales)[number];
type Messages = Record<string, unknown>;

// Helper for deep merging translation objects
function deepMerge(target: Messages, source: Messages): Messages {
    const output = { ...target };

    for (const key in source) {
        if (
            Object.prototype.hasOwnProperty.call(source, key) &&
            source[key] != null &&
            typeof source[key] === 'object' &&
            !Array.isArray(source[key]) &&
            key in target &&
            target[key] != null &&
            typeof target[key] === 'object' &&
            !Array.isArray(target[key])
        ) {
            output[key] = deepMerge(target[key] as Messages, source[key] as Messages);
        } else {
            output[key] = source[key];
        }
    }

    return output;
}

export default getRequestConfig(async ({ locale }) => {
    const resolvedLocale: Locale = locales.includes(locale as Locale) ? (locale as Locale) : defaultLocale;

    // Load base messages (English) and current locale messages
    const baseMessages = await loadLocaleMessages(defaultLocale);
    let messages = baseMessages;

    if (resolvedLocale !== defaultLocale) {
        try {
            const currentMessages = await loadLocaleMessages(resolvedLocale);
            // Deep merge ensures that missing keys in current locale fall back to English
            messages = deepMerge(baseMessages as Messages, currentMessages as Messages) as typeof baseMessages;
        } catch (error) {
            console.error(`Failed to load messages for ${resolvedLocale}, falling back to ${defaultLocale}`, error);
        }
    }

    return {
        locale: resolvedLocale,
        messages
    };
});

const loadLocaleMessages = cache(async function loadLocaleMessages(locale: Locale) {
    const [
        header,
        navigation,
        dashboard,
        users,
        servers,
        placeholder,
        usersTable,
        serversTable,
        serverCard,
        landing,
        footer,
        languageSelector,
        privacyPolicy,
        deleteAccount
    ] = await Promise.all([
        import(`../../messages/${locale}/header.json`),
        import(`../../messages/${locale}/navigation.json`),
        import(`../../messages/${locale}/dashboard.json`),
        import(`../../messages/${locale}/users.json`),
        import(`../../messages/${locale}/servers.json`),
        import(`../../messages/${locale}/placeholder.json`),
        import(`../../messages/${locale}/users-table.json`),
        import(`../../messages/${locale}/servers-table.json`),
        import(`../../messages/${locale}/server-card.json`),
        import(`../../messages/${locale}/landing.json`),
        import(`../../messages/${locale}/footer.json`),
        import(`../../messages/${locale}/language-selector.json`),
        import(`../../messages/${locale}/privacy-policy.json`),
        import(`../../messages/${locale}/delete-account.json`)
    ]);

    return {
        Header: header.default,
        Navigation: navigation.default,
        Dashboard: dashboard.default,
        Users: users.default,
        Servers: servers.default,
        Placeholder: placeholder.default,
        UsersTable: usersTable.default,
        ServersTable: serversTable.default,
        ServerCard: serverCard.default,
        Landing: landing.default,
        Footer: footer.default,
        LanguageSelector: languageSelector.default,
        PrivacyPolicy: privacyPolicy.default,
        DeleteAccount: deleteAccount.default
    };
});
