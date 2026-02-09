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
        deleteAccount,
        auth,
        a11y
    ] = await Promise.all([
        import(`../../messages/${locale}/header.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/navigation.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/dashboard.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/users.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/servers.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/placeholder.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/users-table.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/servers-table.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/server-card.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/landing.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/footer.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/language-selector.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/privacy-policy.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/delete-account.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/auth.json`).catch(() => ({ default: {} })),
        import(`../../messages/${locale}/a11y.json`).catch(() => ({ default: {} }))
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
        DeleteAccount: deleteAccount.default,
        Auth: auth.default,
        A11y: a11y.default
    };
});
