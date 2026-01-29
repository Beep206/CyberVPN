import { getRequestConfig } from 'next-intl/server';
import { defaultLocale, locales } from './config';

type Locale = (typeof locales)[number];

export default getRequestConfig(async ({ locale }) => {
    const resolvedLocale: Locale = locales.includes(locale as Locale) ? (locale as Locale) : defaultLocale;

    const messages = await loadMessages(resolvedLocale);

    return {
        locale: resolvedLocale,
        messages
    };
});

async function loadMessages(locale: Locale) {
    try {
        return await loadLocaleMessages(locale);
    } catch {
        if (locale === defaultLocale) {
            throw new Error(`Missing messages for default locale: ${defaultLocale}`);
        }

        return loadLocaleMessages(defaultLocale);
    }
}

async function loadLocaleMessages(locale: Locale) {
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
        languageSelector
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
        import(`../../messages/${locale}/language-selector.json`)
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
        LanguageSelector: languageSelector.default
    };
}
